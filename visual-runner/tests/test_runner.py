import importlib.metadata
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock

import httpx
from lab.runtime import BrowserLock
from lab.webdriver import DirectWebDriver
from lab.keywords import SmokeLibrary
from lab.sample import serve


class RunnerTests(unittest.TestCase):
    def test_robot_keyword_failure_retains_only_safe_code(self):
        from robot.api import TestSuite
        context = MagicMock()
        context.state = {}
        context.browser.navigate_sample.side_effect = httpx.ReadTimeout('secret-canary')
        suite = TestSuite('Diagnostic regression')
        suite.resource.imports.library('lab.keywords.SmokeLibrary', args=[context])
        suite.tests.create('Failure').body.create_keyword('Open Controlled Sample')
        result = suite.run(output=None, log=None, report=None, console='none')
        self.assertNotEqual(result.return_code, 0)
        self.assertEqual(context.state, {'diagnostic_code': 'ReadTimeout'})
        self.assertNotIn('secret-canary', json.dumps(context.state))
        context.publish.assert_called_once()

    def test_session_read_budget_is_separate_without_retries(self):
        browser = DirectWebDriver.__new__(DirectWebDriver)
        browser.check = lambda: None
        browser.session = 'fixture'
        requests = []
        def handle(request):
            requests.append(request.extensions['timeout'])
            return httpx.Response(200, json={'value': {}})
        with httpx.Client(base_url='http://127.0.0.1:1', timeout=5, transport=httpx.MockTransport(handle)) as client:
            browser.client = client
            browser.call('POST', '/session', {})
            browser.call('GET', '/status')
            browser.call('POST', '/session/fixture/url', {'url': 'http://127.0.0.1:1/'})
            browser.call('GET', '/session/fixture/url')
        self.assertEqual(len(requests), 4)
        self.assertEqual(requests[0], {'connect': 5, 'read': 45, 'write': 5, 'pool': 5})
        self.assertEqual(requests[1]['read'], 5)
        self.assertEqual(requests[2]['read'], 12)
        self.assertEqual(requests[3]['read'], 5)

    def test_startup_observations_do_not_read_port_contents_or_publish_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            browser = DirectWebDriver.__new__(DirectWebDriver)
            browser.workspace = Path(folder)
            (browser.workspace / 'profile').mkdir()
            (browser.workspace / 'profile' / 'DevToolsActivePort').write_text('secret-canary')
            browser.driver_version = '146.0.7680.31'
            browser.process = MagicMock()
            browser.process.poll.return_value = None
            browser.tree = MagicMock()
            browser.tree.browser_status.return_value = 'running'
            browser.session = None
            browser.native_errors = set()
            browser.errors_lock = threading.Lock()
            snapshots = []
            browser.telemetry = snapshots.append
            browser.capture()
            self.assertEqual(snapshots[-1]['devtools_port_file'], 'present')
            self.assertEqual(snapshots[-1]['browser_state'], 'running')
            self.assertFalse(snapshots[-1]['session_created'])
            self.assertNotIn('secret-canary', json.dumps(snapshots))
            self.assertNotIn(folder, json.dumps(snapshots))
            browser.process.poll.return_value = 1
            browser.tree.browser_status.return_value = 'exited'
            browser.capture('driver_exited_job_closed')
            self.assertEqual(snapshots[-1]['cleanup_driver_exit_code'], 1)
            self.assertEqual(snapshots[-1]['cleanup_browser_state'], 'exited')
            self.assertNotIn('browser_state', snapshots[-1])  # Preserve failure-time sample.

    def test_native_output_is_reduced_to_fixed_categories(self):
        browser = DirectWebDriver.__new__(DirectWebDriver)
        browser.process = MagicMock()
        browser.process.stderr = io.StringIO('Launching chrome: secret-canary\nAccess is denied secret-canary\n')
        browser.native_errors = set()
        browser.errors_lock = threading.Lock()
        events = []
        browser.diagnostic = lambda *args: events.append(args)
        browser.observe_driver()
        self.assertEqual(browser.native_errors, {'access_denied'})
        self.assertEqual(events, [('browser_launch',)])
        self.assertNotIn('secret-canary', json.dumps(events))

    def test_ready_requires_protocol_true_and_live_driver(self):
        browser = DirectWebDriver.__new__(DirectWebDriver)
        browser.check = lambda: None
        browser.process = MagicMock()
        browser.process.poll.return_value = None
        replies = iter([False, True])
        seen = []
        def handle(request):
            seen.append(request.url.path)
            return httpx.Response(200, json={'value': {'ready': next(replies)}})
        browser.client = httpx.Client(base_url='http://127.0.0.1:1', transport=httpx.MockTransport(handle))
        browser.wait_ready()
        self.assertEqual(len(seen), 2)
        browser.process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, 'DRIVER_START_FAILED'): browser.wait_ready()
        browser.client.close()

    def test_sample_proxy_rejects_external_targets_and_tunnels(self):
        server, origin = serve()
        try:
            with httpx.Client(proxy=origin.rstrip('/'), trust_env=False) as client:
                self.assertEqual(client.get(origin).status_code, 200)
                self.assertEqual(client.get('http://169.254.169.254/').status_code, 403)
                self.assertEqual(client.get('http://example.com/').status_code, 403)
                with self.assertRaises(httpx.ProxyError):
                    client.get('https://example.com/')
        finally:
            server.shutdown()
            server.server_close()

    def test_installed_graph_is_exact_and_excludes_prohibited_clients(self):
        allowed = {'pip', 'robotframework', 'httpx', 'anyio', 'certifi', 'httpcore', 'idna',
                   'h11', 'sniffio', 'typing-extensions'}
        installed = {d.metadata['Name'].lower().replace('_', '-') for d in importlib.metadata.distributions()}
        self.assertEqual(installed, allowed)

    def test_kernel_lock_excludes_duplicate_and_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'lock'
            lock = BrowserLock(path)
            with self.assertRaisesRegex(RuntimeError, 'BROWSER_BUSY'):
                BrowserLock(path)
            lock.close()
            BrowserLock(path).close()

    def test_protocol_actions_have_no_selectors_or_scripts(self):
        browser = DirectWebDriver.__new__(DirectWebDriver)
        browser.session = 'fixture'
        browser.check = lambda: None
        seen = []
        def handle(request):
            seen.append((request.method, request.url.path, request.content))
            return httpx.Response(200, json={'value': None})
        browser.client = httpx.Client(base_url='http://127.0.0.1:1', transport=httpx.MockTransport(handle))
        browser.click(150, 200)
        browser.keys('abc')
        with self.assertRaisesRegex(RuntimeError, 'OUT_OF_BOUNDS'):
            browser.click(-1, 200)
        self.assertTrue(all(path.endswith('/actions') for _, path, _ in seen))
        browser.client.close()

    def test_fixed_robot_interface(self):
        self.assertFalse(SmokeLibrary.ROBOT_AUTO_KEYWORDS)
        names = {getattr(method, 'robot_name') for method in vars(SmokeLibrary).values() if hasattr(method, 'robot_name')}
        self.assertEqual(len(names), 4)


if __name__ == '__main__':
    unittest.main()
