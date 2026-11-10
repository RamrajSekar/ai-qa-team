"""Small W3C WebDriver subset. No selectors, script execution or arbitrary navigation."""
import base64
import re
import socket
import subprocess
import time
import threading
from pathlib import Path

import httpx
from lab.runtime import WindowsProcessTree


# Separate protocol budgets; do not retry a timed-out action.
SESSION_READ_SECONDS = 45
PAGE_LOAD_MILLISECONDS = 10000
NAVIGATION_READ_SECONDS = PAGE_LOAD_MILLISECONDS / 1000 + 2  # Allow the driver's timeout response.


class DirectWebDriver:
    def __init__(self, chrome: str, driver: str, sample_url: str, headed: bool, workspace: Path, check, diagnostic=None, telemetry=None, tree_factory=WindowsProcessTree):
        self.check, self.sample_url = check, sample_url
        self.diagnostic = diagnostic or (lambda *args: None)
        self.telemetry = telemetry or (lambda *args: None)
        self.workspace = workspace
        self.driver_version = None
        self.native_errors = set()
        self.errors_lock = threading.Lock()
        self.observer = None
        self.session = None
        self.tree = tree_factory()
        self.process = None
        self.client = None
        try:
            self.diagnostic('driver_version')
            # Fail closed on mismatched release builds (not just major version).
            version = subprocess.check_output([driver, '--version'], timeout=5, text=True)
            driver_version = re.search(r'\d+\.\d+\.\d+\.\d+', version).group()
            self.driver_version = driver_version
            # CfT layout has a versioned parent; actual browser version checked again after session creation.
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            self.diagnostic('driver_launch')
            self.process = self.tree.launch([driver, f'--port={port}', '--allowed-ips=127.0.0.1', '--verbose'],
                                           stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
            self.observer = threading.Thread(target=self.observe_driver, daemon=True)
            self.observer.start()
            self.client = httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=5, trust_env=False)
            self.diagnostic('driver_readiness')
            self.wait_ready()
            args = ['--window-size=1000,800', '--force-device-scale-factor=1', '--lang=en-US',
                    '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
                    '--disable-component-update', '--disable-sync', '--disable-extensions',
                    '--disable-features=Translate,MediaRouter', '--disable-quic',
                    f'--proxy-server={sample_url.rstrip("/")}', '--proxy-bypass-list=<-loopback>',
                    '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',
                    f'--user-data-dir={workspace / "profile"}']
            if not headed:
                args.append('--headless=new')
            self.diagnostic('session_creation')
            value = self.call('POST', '/session', {'capabilities': {'alwaysMatch': {
                'browserName': 'chrome', 'goog:chromeOptions': {'binary': chrome, 'args': args}}}})
            self.session = value['sessionId']
            self.diagnostic('version_validation')
            if value['capabilities']['browserVersion'] != driver_version:
                raise RuntimeError('BROWSER_DRIVER_MISMATCH')
            self.version = driver_version
            self.diagnostic('session_timeouts')
            self.command('POST', 'timeouts', {'implicit': 0, 'pageLoad': PAGE_LOAD_MILLISECONDS, 'script': 1000})
            self.diagnostic('ready')
            self.capture()
        except BaseException:
            self.close()
            raise

    def capture(self, cleanup='not_started'):
        # Existence only: never read/publish DevTools port, websocket URL or profile paths.
        try:
            port_file = 'present' if (self.workspace / 'profile' / 'DevToolsActivePort').is_file() else 'absent'
        except OSError:
            port_file = 'unavailable'
        code = self.process.poll() if self.process else None
        with self.errors_lock:
            native_errors = sorted(self.native_errors)
        try:
            browser_state = self.tree.browser_status()
        except (OSError, ValueError):
            browser_state = 'unavailable'
        if cleanup != 'not_started':
            self.telemetry({'cleanup': cleanup, 'cleanup_driver_exit_code': code,
                            'cleanup_browser_state': browser_state, 'native_errors': native_errors})
            return
        self.telemetry({'driver_version': self.driver_version,
            'driver_state': 'not_started' if not self.process else 'running' if code is None else 'exited',
            'driver_exit_code': code, 'browser_state': browser_state,
            'devtools_port_file': port_file, 'session_created': self.session is not None,
            'cleanup': cleanup, 'native_errors': native_errors})

    def call(self, method, path, payload=None):
        self.check()
        # Cold Windows CfT initialization was measured at >24 seconds. Only session
        # creation gets this startup budget; navigation also honors the driver page-load budget.
        timeout = self.client.timeout
        if method == 'POST' and path == '/session':
            timeout = httpx.Timeout(5, read=SESSION_READ_SECONDS)
        elif method == 'POST' and self.session and path == f'/session/{self.session}/url':
            timeout = httpx.Timeout(5, read=NAVIGATION_READ_SECONDS)
        response = self.client.request(method, path, json=payload, timeout=timeout)
        value = response.json().get('value')
        if response.status_code >= 400 or isinstance(value, dict) and value.get('error'):
            message = str(value.get('message', '')).lower() if isinstance(value, dict) else ''
            reason = next((label for needle, label in (
                ('chrome instance exited', 'browser_exited'), ('chrome failed to start', 'browser_exited'),
                ('devtoolsactiveport', 'devtools_port_missing'), ('user data directory is already in use', 'profile_in_use'),
                ('cannot connect to chrome', 'browser_unreachable'), ('disconnected', 'browser_disconnected')) if needle in message), None)
            if reason:
                self.diagnostic(None, reason)
            code = {'session not created': 'BROWSER_SESSION_NOT_CREATED', 'invalid session id': 'BROWSER_SESSION_LOST',
                    'timeout': 'WEBDRIVER_TIMEOUT'}.get(value.get('error') if isinstance(value, dict) else None, 'WEBDRIVER_COMMAND_FAILED')
            raise RuntimeError(code)
        return value

    def wait_ready(self):
        deadline = time.monotonic() + 6  # Same intended readiness budget; not a workflow/session retry.
        while time.monotonic() < deadline:
            self.check()
            if self.process.poll() is not None:
                raise RuntimeError('DRIVER_START_FAILED')
            try:
                response = self.client.get('/status', timeout=.25)
                if response.status_code == 200 and response.json().get('value', {}).get('ready') is True:
                    return
            except (httpx.TransportError, ValueError):
                pass
            time.sleep(.1)
        raise RuntimeError('DRIVER_START_FAILED')

    def observe_driver(self):
        # Raw output is consumed in memory and discarded. Only fixed stage/reason enums escape.
        seen = set()
        for line in iter(lambda: self.process.stderr.readline(8192), ''):
            # Only static categories escape this stream. No raw lines are retained.
            for marker, category in (('Access is denied', 'access_denied'),
                    ('Permission denied', 'access_denied'), ('DevToolsActivePort file doesn', 'devtools_port_missing'),
                    ('Chrome failed to start', 'browser_exited'), ('chrome instance exited', 'browser_exited'),
                    ('user data directory is already in use', 'profile_in_use')):
                if marker in line:
                    with self.errors_lock:
                        self.native_errors.add(category)
            stage = next((label for marker, label in (
                ('Launching chrome:', 'browser_launch'), ('DevTools HTTP Request:', 'devtools_connect'),
                ('DevTools HTTP Response:', 'session_handshake')) if marker in line), None)
            if stage and stage not in seen:
                seen.add(stage)
                self.diagnostic(stage)

    def command(self, method, suffix, payload=None):
        return self.call(method, f'/session/{self.session}/{suffix}', payload)

    def navigate_sample(self):
        self.diagnostic('navigation')
        self.command('POST', 'url', {'url': self.sample_url})
        self.diagnostic('navigation_checkpoint')
        if self.command('GET', 'url') != self.sample_url:
            raise RuntimeError('SAMPLE_ORIGIN_CHANGED')

    def click(self, x, y):
        if not (0 <= x < 1000 and 0 <= y < 600):
            raise RuntimeError('COORDINATE_OUT_OF_BOUNDS')
        self.command('POST', 'actions', {'actions': [{'type': 'pointer', 'id': 'mouse',
            'parameters': {'pointerType': 'mouse'}, 'actions': [
                {'type': 'pointerMove', 'duration': 0, 'origin': 'viewport', 'x': x, 'y': y},
                {'type': 'pointerDown', 'button': 0}, {'type': 'pointerUp', 'button': 0}]}]})

    def keys(self, text):
        actions = []
        for char in text:
            actions.extend([{'type': 'keyDown', 'value': char}, {'type': 'keyUp', 'value': char}])
        self.command('POST', 'actions', {'actions': [{'type': 'key', 'id': 'keyboard', 'actions': actions}]})

    def screenshot(self, destination):
        self.diagnostic('screenshot')
        destination.write_bytes(base64.b64decode(self.command('GET', 'screenshot'), validate=True))

    def close(self):
        try:
            self.capture()
            if self.session and self.client:
                # Cleanup bypasses cancellation checks, but transport remains bounded.
                self.client.delete(f'/session/{self.session}')
        except Exception:
            pass
        finally:
            try:
                if self.client:
                    self.client.close()
            finally:
                self.tree.close()
                try:
                    if self.process:
                        self.process.wait(timeout=5)
                    if self.observer:
                        self.observer.join(timeout=.5)
                    # Poll cleanup, not browser startup or workflow retries.
                    deadline = time.monotonic() + 1
                    while self.tree.browser_status() == 'running' and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.capture('driver_exited_job_closed' if self.process and self.process.poll() is not None
                                 and self.tree.browser_status() == 'exited' else 'unverified')
                finally:
                    self.tree.release_observations()
