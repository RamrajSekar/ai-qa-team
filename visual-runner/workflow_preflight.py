"""Fixed Robot/browser readiness operation. Never executes the manifest's actions."""
import io
import importlib.metadata
import json
import re
import signal
import sys
import time

import httpx
from robot.api import TestSuite
from robot.api.deco import keyword, library

CONTEXT = None
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")


def emit(value):
    # Robot redirects sys.stdout while keywords run. Protocol events must reach
    # the private parent pipe immediately, including before a crash/cancellation.
    print(json.dumps(value, separators=(",", ":")), file=sys.__stdout__, flush=True)


class BrowserStackAdapter:
    """Small replaceable transport; only readiness methods are exposed to Robot."""
    def __init__(self, credentials, on_session, client=None):
        self.client = client or httpx.Client(base_url="https://hub-cloud.browserstack.com/wd/hub/",
            auth=(credentials["username"], credentials["access_key"]),
            timeout=httpx.Timeout(5, read=10), trust_env=False)
        self.session = None
        self.on_session = on_session
        self.cleanup_confirmed = True
        self.deadline = time.monotonic() + 65

    def call(self, method, path, body=None, session_creation=False):
        if time.monotonic() >= self.deadline:
            raise RuntimeError("PREFLIGHT_DEADLINE")
        response = self.client.request(method, path, json=body,
            timeout=httpx.Timeout(5, read=30 if session_creation else 10))
        if not response.is_success:
            raise RuntimeError("REMOTE_COMMAND_REJECTED")
        value = response.json()["value"]
        if isinstance(value, dict) and value.get("error"):
            raise RuntimeError("REMOTE_COMMAND_REJECTED")
        return value

    def open(self):
        self.cleanup_confirmed = False
        result = self.call("POST", "session", {"capabilities": {"alwaysMatch": {
            "browserName": "chrome", "bstack:options": {"os": "Windows", "osVersion": "11",
                "idleTimeout": 60, "projectName": "AI QA Squad development",
                "sessionName": "Approved manifest browser readiness"},
        }}}, session_creation=True)
        identity = result.get("sessionId")
        if not isinstance(identity, str) or not SESSION_PATTERN.fullmatch(identity):
            raise RuntimeError("REMOTE_SESSION_INVALID")
        self.session = identity
        self.on_session(identity)  # Private parent channel, never a public API field.

    def verify_blank(self):
        self.call("POST", f"session/{self.session}/url", {"url": "about:blank"})
        if self.call("GET", f"session/{self.session}/url") != "about:blank":
            raise RuntimeError("PREFLIGHT_ORIGIN_REJECTED")

    def close(self):
        try:
            if self.session:
                # Cleanup has its own bounded HTTP budget even if the work deadline expired.
                response = self.client.delete(f"session/{self.session}", timeout=httpx.Timeout(5, read=10))
                value = response.json().get("value")
                error = value.get("error") if isinstance(value, dict) else None
                self.cleanup_confirmed = (response.is_success and not error) or error == "invalid session id"
        except Exception:
            self.cleanup_confirmed = False
        finally:
            self.client.close()


@library(auto_keywords=False)
class ReadinessLibrary:
    @keyword("Open Isolated Readiness Browser")
    def open_browser(self):
        CONTEXT.open()

    @keyword("Verify Blank Readiness Page")
    def verify_blank(self):
        CONTEXT.verify_blank()


def execute(adapter):
    global CONTEXT
    CONTEXT = adapter
    sys.modules["workflow_preflight"] = sys.modules[__name__]
    suite = TestSuite("Approved manifest browser readiness")
    suite.resource.imports.library("workflow_preflight.ReadinessLibrary")
    case = suite.tests.create("Readiness only; no approved actions or assertions executed")
    case.body.create_keyword("Open Isolated Readiness Browser")
    case.body.create_keyword("Verify Blank Readiness Page")
    try:
        result = suite.run(output=None, log=None, report=None, console="none", stdout=io.StringIO(), stderr=io.StringIO())
        return result.return_code == 0
    finally:
        adapter.close()
        CONTEXT = None


def main():
    adapter = None
    ready = False
    reason = "BROWSER_PREFLIGHT_FAILED"
    try:
        installed = {re.sub(r"[-_.]+", "-", package.metadata["Name"]).lower(): package.version
                     for package in importlib.metadata.distributions()}
        prohibited = ("selenium", "playwright", "puppeteer", "robotframework-selenium", "robotframework-browser")
        if any(name.startswith(prohibited) for name in installed):
            raise ValueError("Prohibited runner dependency")
        if installed.get("robotframework") != "7.5" or installed.get("httpx") != "0.28.1":
            raise ValueError("Unqualified runner dependency versions")
        raw = sys.stdin.buffer.readline(260001)
        if len(raw) > 260000:
            raise ValueError("Payload limit")
        payload = json.loads(raw)
        if (payload.get("operation") != "browser-readiness-v1"
                or payload.get("adapter") != "browserstack-direct-webdriver-v1"
                or not re.fullmatch(r"[0-9a-f]{64}", payload.get("manifest_digest", ""))
                or not isinstance(payload.get("manifest"), dict)):
            raise ValueError("Unsupported operation")
        # The manifest is consumed as immutable input identity, never as code or a destination.
        manifest = payload["manifest"]
        if manifest.get("runtime_contract") != "robot-visual-workflow-v1":
            raise ValueError("Unsupported runtime contract")
        credentials = payload["provider_credentials"]
        if not all(isinstance(credentials.get(key), str) and credentials[key] for key in ("username", "access_key")):
            raise ValueError("Missing transport configuration")
        adapter = BrowserStackAdapter(credentials, lambda identity: emit({"event": "session", "session_id": identity}))
        ready = execute(adapter)
        if ready:
            reason = "ACTION_RUNTIME_NOT_ENABLED"
    except BaseException:
        # No exception text, raw Robot output, capabilities, URLs or provider messages escape.
        if adapter:
            adapter.close()
    emit({"event": "result", "browser_ready": ready,
          "cleanup_confirmed": adapter.cleanup_confirmed if adapter else True, "reason": reason})
    return 0 if ready else 1


if __name__ == "__main__":
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(1)))
    raise SystemExit(main())
