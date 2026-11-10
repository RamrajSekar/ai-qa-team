"""One-shot remote startup and rendering probe for the synthetic fixture."""
import base64
import os
from pathlib import Path
import re

import httpx

from lab.sample import HTML


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
                response = client.request(method, path, json=payload)
                if not response.is_success:
                    raise RuntimeError(f'HTTP {response.status_code}')
                return response.json()['value']

            session = command('POST', 'session', {'capabilities': {'alwaysMatch': {
                'browserName': 'chrome',
                'bstack:options': {
                    'os': 'Windows', 'osVersion': '11',
                    'projectName': 'AI QA Squad', 'sessionName': 'Synthetic fixture rendering probe',
                    'idleTimeout': 60,
                },
            }}})['sessionId']
            if not re.fullmatch(r'[a-zA-Z0-9-]{1,128}', session):
                raise RuntimeError('Unexpected session identifier')
            route = f'session/{session}'
            try:
                stage = 'navigation'
                fixture = 'data:text/html;base64,' + base64.b64encode(HTML).decode('ascii')
                command('POST', f'{route}/url', {'url': fixture})
                if command('GET', f'{route}/title') != 'QA Lab sample':
                    raise RuntimeError('Unexpected synthetic fixture title')
                stage = 'screenshot'
                png = base64.b64decode(command('GET', f'{route}/screenshot'), validate=True)
                if not png.startswith(b'\x89PNG\r\n\x1a\n') or len(png) > 8_000_000:
                    raise RuntimeError('Invalid screenshot')
                Path(os.environ['RUNNER_TEMP'], 'browserstack-fixture.png').write_bytes(png)
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

    print('BrowserStack opened the synthetic fixture and captured a screenshot.')


if __name__ == '__main__':
    main()
