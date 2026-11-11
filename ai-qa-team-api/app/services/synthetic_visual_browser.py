"""One remote WebDriver session against a fixed, offline synthetic fixture."""
import asyncio
import base64
from io import BytesIO
import re
import secrets

import httpx
from PIL import Image, ImageChops, ImageDraw


BUTTON = 'Save draft'
INITIAL = 'Ready'
CONFIRMATION = 'Draft saved'
PALETTES = ((46, 70, 162), (21, 105, 75))
STATUS_COLOR = (62, 44, 78)


def tile(text, color, size):
    image = Image.new('RGB', size, color)
    ImageDraw.Draw(image).text((16, size[1] // 2), text, fill='white', anchor='lm', font_size=20)
    return image


def data_uri(data, media_type):
    return f'data:{media_type};base64,' + base64.b64encode(data).decode('ascii')


def png_uri(image):
    data = BytesIO()
    image.save(data, format='PNG')
    return data_uri(data.getvalue(), 'image/png')


def fixture():
    color = secrets.choice(PALETTES)
    left = secrets.choice((70, 260, 430))
    top = secrets.choice((130, 240, 350))
    button = tile(BUTTON, color, (200, 52))
    ready = tile(INITIAL, STATUS_COLOR, (250, 46))
    saved = tile(CONFIRMATION, STATUS_COLOR, (250, 46))
    html = f"""<!doctype html><meta charset=utf-8><title>Synthetic draft fixture</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<h1>Synthetic draft fixture</h1>
<button style="position:absolute;left:{left}px;top:{top}px;padding:0;border:0;background:none"
onclick="document.getElementById('result').src='{png_uri(saved)}';this.disabled=true">
<img style="display:block" alt="{BUTTON}" src="{png_uri(button)}"></button>
<img id="result" style="position:absolute;left:{left}px;top:{top + 75}px"
 alt="Synthetic status" src="{png_uri(ready)}">"""
    return data_uri(html.encode(), 'text/html'), button, color, {INITIAL: ready, CONFIRMATION: saved}


def exact_tile(image, color, templates):
    # Color identifies a candidate area. The complete raster must match exactly.
    mask = Image.frombytes('L', image.size, bytes(
        255 if pixel == color else 0 for pixel in image.getdata()
    ))
    bounds = mask.getbbox()
    if not bounds:
        return None
    crop = image.crop(bounds)
    for text, template in templates.items():
        if crop.size == template.size and not ImageChops.difference(crop, template).getbbox():
            return text, bounds
    return None


class RemoteSyntheticBrowser:
    def __init__(self, username, key):
        self.client = httpx.AsyncClient(
            base_url='https://hub-cloud.browserstack.com/wd/hub/',
            auth=(username, key), timeout=httpx.Timeout(8, read=12), trust_env=False,
        )
        self.session = None
        self.cleanup_confirmed = True

    async def call(self, method, path, body=None, *, timeout=None):
        response = await self.client.request(method, path, json=body, timeout=timeout or self.client.timeout)
        response.raise_for_status()
        value = response.json()['value']
        if isinstance(value, dict) and value.get('error'):
            raise RuntimeError('REMOTE_COMMAND_REJECTED')
        return value

    async def command(self, method, path, body=None):
        return await self.call(method, f'session/{self.session}/{path}', body)

    async def open(self):
        self.cleanup_confirmed = False
        value = await self.call('POST', 'session', {'capabilities': {'alwaysMatch': {
            'browserName': 'chrome',
            'goog:chromeOptions': {'args': ['--force-device-scale-factor=1']},
            'bstack:options': {'os': 'Windows', 'osVersion': '11', 'idleTimeout': 60,
                               'projectName': 'AI QA Squad', 'sessionName': 'Approved synthetic draft check'},
        }}}, timeout=httpx.Timeout(8, read=30))
        session = value['sessionId']
        if not isinstance(session, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,128}', session):
            raise RuntimeError('REMOTE_SESSION_INVALID')
        self.session = session

    async def close(self):
        try:
            if self.session:
                await self.call('DELETE', f'session/{self.session}')
                self.cleanup_confirmed = True
        finally:
            await self.client.aclose()

    async def screenshot(self):
        encoded = await self.command('GET', 'screenshot')
        if not isinstance(encoded, str) or len(encoded) > 1_300_000:
            raise RuntimeError('SCREENSHOT_LIMIT')
        raw = base64.b64decode(encoded, validate=True)
        with Image.open(BytesIO(raw), formats=('PNG',)) as source:
            if not (0 < source.width <= 1200 and 0 < source.height <= 1000):
                raise RuntimeError('VIEWPORT_LIMIT')
            return raw, source.convert('RGB')

    async def execute(self, label, expected, checkpoint):
        if label != BUTTON:
            return 'needs_review', None, None, 'UNSUPPORTED_SYNTHETIC_LABEL'
        url, button, color, status_tiles = fixture()
        await checkpoint()
        await self.open()
        await checkpoint()
        await self.command('POST', 'window/rect', {'width': 1000, 'height': 800})
        await self.command('POST', 'url', {'url': url})
        before, image = await self.screenshot()
        match = exact_tile(image, color, {BUTTON: button})
        if not match:
            return 'needs_review', None, before, 'BUTTON_NOT_UNIQUE'
        _, (left, top, right, bottom) = match
        x, y = (left + right) // 2, (top + bottom) // 2
        if not (0 <= x < 1000 and 0 <= y < 600):
            return 'needs_review', None, before, 'BUTTON_OUT_OF_BOUNDS'
        if await self.command('GET', 'url') != url or (await self.screenshot())[0] != before:
            return 'needs_review', None, before, 'OBSERVATION_STALE'
        await checkpoint()
        # Never replay this input if its response is lost.
        try:
            await self.command('POST', 'actions', {'actions': [{
                'type': 'pointer', 'id': 'mouse', 'parameters': {'pointerType': 'mouse'},
                'actions': [{'type': 'pointerMove', 'origin': 'viewport', 'x': x, 'y': y, 'duration': 0},
                            {'type': 'pointerDown', 'button': 0}, {'type': 'pointerUp', 'button': 0}],
            }]})
        except (httpx.HTTPError, ValueError, RuntimeError):
            return 'needs_review', None, before, 'CLICK_OUTCOME_UNCERTAIN'
        await checkpoint()
        await asyncio.sleep(0.25)
        try:
            if await self.command('GET', 'url') != url:
                return 'needs_review', None, before, 'OBSERVATION_STALE'
            after, result = await self.screenshot()
        except (httpx.HTTPError, OSError, ValueError, RuntimeError):
            return 'needs_review', None, None, 'ASSERTION_EVIDENCE_UNAVAILABLE'
        observed = exact_tile(result, STATUS_COLOR, status_tiles)
        if not observed:
            return 'needs_review', None, after, 'ASSERTION_EVIDENCE_UNREADABLE'
        text, _ = observed
        return ('passed' if text == expected else 'failed'), text, after, None
