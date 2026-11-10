"""One-shot remote mechanical workflow for the synthetic fixture."""
import base64
import os
from pathlib import Path
import re
import time

import httpx

from lab.keywords import SmokeLibrary
from lab.sample import HTML
from lab.webdriver import DirectWebDriver


class RemoteFixtureBrowser(DirectWebDriver):
    """Reuse the fixed WebDriver actions with the remote probe's transport."""

    def __init__(self, command, session, fixture):
        self.call = command
        self.session = session
        self.sample_url = fixture
        self.diagnostic = lambda *_: None

    def navigate_sample(self):
        self.command('POST', 'url', {'url': self.sample_url})
        if self.command('GET', 'title') != 'QA Lab sample':
            raise RuntimeError('Unexpected synthetic fixture title')
        if self.command('GET', 'url') != self.sample_url:
            raise RuntimeError('Synthetic fixture URL changed')

    def screenshot(self, destination):
        png = base64.b64decode(self.command('GET', 'screenshot'), validate=True)
        if not png.startswith(b'\x89PNG\r\n\x1a\n') or len(png) > 8_000_000:
            raise RuntimeError('Invalid screenshot')
        destination.write_bytes(png)


class FixtureContext:
    def __init__(self, browser, evidence):
        self.browser = browser
        self.evidence = evidence
        self.state = {}

    pause = staticmethod(time.sleep)

    def snapshot(self, name):
        self.pause(0.4)
        self.browser.screenshot(self.evidence / f'{name}.png')

    def publish(self):
        pass  # The outer probe reports the failed stage without provider details.


def main():
    username = os.environ.get('BROWSERSTACK_USERNAME')
    access_key = os.environ.get('BROWSERSTACK_ACCESS_KEY')
    if not username or not access_key:
        raise SystemExit('Missing BrowserStack Automate credentials in Actions secrets.')

    stage = 'session'
    try:
        with httpx.Client(
            base_url='https://hub-cloud.browserstack.com/wd/hub/',
            auth=(username, access_key), timeout=httpx.Timeout(10, read=60),
            trust_env=False,
        ) as client:
            def command(method, path, payload=None):
                response = client.request(method, path.lstrip('/'), json=payload)
                if not response.is_success:
                    raise RuntimeError(f'HTTP {response.status_code}')
                return response.json()['value']

            session = command('POST', 'session', {'capabilities': {'alwaysMatch': {
                'browserName': 'chrome',
                'bstack:options': {
                    'os': 'Windows', 'osVersion': '11',
                    'projectName': 'AI QA Squad', 'sessionName': 'Synthetic form smoke check',
                    'idleTimeout': 60,
                },
            }}})['sessionId']
            if not re.fullmatch(r'[a-zA-Z0-9-]{1,128}', session):
                raise RuntimeError('Unexpected session identifier')
            route = f'session/{session}'
            try:
                fixture = 'data:text/html;base64,' + base64.b64encode(HTML).decode('ascii')
                evidence = Path(os.environ['RUNNER_TEMP'], 'browserstack-fixture')
                evidence.mkdir(exist_ok=True)
                browser = RemoteFixtureBrowser(command, session, fixture)
                workflow = SmokeLibrary(FixtureContext(browser, evidence))
                stage = 'window_setup'
                browser.command('POST', 'window/rect', {'width': 1000, 'height': 800})
                stage = 'navigation'
                workflow.open_sample()
                stage = 'form_input'
                workflow.fill_form()
                stage = 'confirmation'
                workflow.confirm()
            finally:
                try:
                    command('DELETE', route)
                except Exception:
                    print('BrowserStack session cleanup could not be confirmed.')
                    raise
    except Exception as exc:
        # Provider responses and request details can include credentials.
        detail = str(exc) if re.fullmatch(r'HTTP [0-9]{3}', str(exc)) else type(exc).__name__
        raise SystemExit(f'BrowserStack probe failed at {stage}: {detail}') from None

    print('Browser smoke check completed')


if __name__ == '__main__':
    main()
