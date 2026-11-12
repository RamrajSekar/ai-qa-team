"""Actual Robot keyword execution, mocked HTTPX transport; no real BrowserStack calls."""
from pathlib import Path
import sys
import json
import subprocess
from io import StringIO
from unittest.mock import patch
import unittest

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workflow_preflight import BrowserStackAdapter, execute, emit


class ReadinessTests(unittest.TestCase):
    def adapter(self, fail=False):
        self.requests = []; self.events = []
        def handle(request):
            self.requests.append(request)
            if request.url.path.endswith("/session") and request.method == "POST":
                return httpx.Response(200, json={"value": {"sessionId": "synthetic-session"}})
            if request.method == "DELETE":
                return httpx.Response(200, json={"value": None})
            return httpx.Response(200, json={"value": "wrong" if fail else "about:blank"})
        client = httpx.Client(base_url="https://fixture.test/wd/hub/", transport=httpx.MockTransport(handle))
        return BrowserStackAdapter({"username": "synthetic", "access_key": "synthetic"}, self.events.append, client)

    def test_fixed_robot_library_only_opens_blank_and_closes(self):
        adapter = self.adapter()
        self.assertTrue(execute(adapter))
        self.assertTrue(adapter.cleanup_confirmed)
        self.assertEqual(self.events, ["synthetic-session"])
        self.assertEqual(self.requests[-1].method, "DELETE")
        import json
        self.assertEqual(json.loads(self.requests[1].content), {"url": "about:blank"})
        self.assertFalse(any("execute" in str(request.url) or "element" in str(request.url) for request in self.requests))

    def test_wrong_page_fails_robot_but_still_closes(self):
        adapter = self.adapter(fail=True)
        self.assertFalse(execute(adapter))
        self.assertTrue(adapter.cleanup_confirmed)
        self.assertEqual(self.requests[-1].method, "DELETE")

    def test_session_event_bypasses_robot_stdout_capture(self):
        adapter = self.adapter()
        adapter.on_session = lambda identity: emit({"event": "session", "session_id": identity})
        private_pipe = StringIO()
        with patch.object(sys, "__stdout__", private_pipe):
            self.assertTrue(execute(adapter))
        self.assertEqual(json.loads(private_pipe.getvalue()), {"event": "session", "session_id": "synthetic-session"})

    def test_invalid_manifest_never_echoes_secret_or_accepts_arbitrary_operation(self):
        script = Path(__file__).resolve().parents[1] / "workflow_preflight.py"
        payload = {"operation": "run-arbitrary-code", "provider_credentials": {"access_key": "SECRET_CANARY"},
                   "manifest": {"target_url": "https://forbidden.invalid/SECRET_CANARY"}}
        result = subprocess.run([sys.executable, "-I", str(script)], input=json.dumps(payload)+"\n", capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("SECRET_CANARY", result.stdout + result.stderr)
        self.assertNotIn("forbidden.invalid", result.stdout + result.stderr)
        event = json.loads(result.stdout)
        self.assertFalse(event["browser_ready"])
        self.assertTrue(event["cleanup_confirmed"])
