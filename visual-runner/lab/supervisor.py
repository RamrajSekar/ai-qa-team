"""Isolated runner entrypoint with bounded heartbeat supervision and Job Object cleanup."""
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

from robot.api import TestSuite
from lab.runtime import BrowserLock, atomic_json
from lab.sample import serve
from lab.webdriver import DirectWebDriver

TERMINAL = {'completed', 'failed', 'cancelled', 'interrupted', 'timed_out'}


class Context:
    def __init__(self, workspace, timeout):
        self.workspace, self.timeout = workspace, timeout
        self.start = time.monotonic()
        self.browser = None
        self.state = {'state': 'starting', 'logs': [], 'screenshots': [], 'browser_version': None}
        self.reason = None
        self.done = threading.Event()
        self.phase_started = self.start
        self.publish_lock = threading.RLock()

    def diagnostic(self, stage, reason=None):
        with self.publish_lock:
            self._diagnostic(stage, reason)

    def telemetry(self, fields):
        with self.publish_lock:
            self.state.setdefault('startup_diagnostics', {}).update(fields)
            # Include the terminal/failing phase, which has no subsequent transition.
            stage = self.state.get('startup_stage')
            if stage and fields.get('cleanup') == 'not_started':
                self.state.setdefault('startup_timings_ms', {})[stage] = round((time.monotonic()-self.phase_started)*1000)
            self.publish()

    def _diagnostic(self, stage, reason=None):
        if stage:
            previous = self.state.get('startup_stage')
            if previous:
                self.state.setdefault('startup_timings_ms', {})[previous] = round((time.monotonic()-self.phase_started)*1000)
            self.phase_started = time.monotonic()
            self.state['startup_stage'] = stage
        if reason:
            self.state['startup_reason'] = reason
        self.publish()

    def check(self):
        if (self.workspace / 'cancel').exists():
            self.reason = 'cancelled'
        elif time.monotonic() - self.start > self.timeout:
            self.reason = 'timed_out'
        else:
            try:
                if time.time() - (self.workspace / 'heartbeat').stat().st_mtime > 6:
                    self.reason = 'interrupted'
            except OSError:
                self.reason = 'interrupted'
        if self.reason:
            raise RuntimeError(self.reason.upper())

    def publish(self, state=None, message=None):
        with self.publish_lock:
            if state:
                self.state['state'] = state
            if message:
                self.state['logs'].append(message)
            atomic_json(self.workspace / 'state.json', self.state)

    def pause(self, seconds):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            self.check()
            time.sleep(.1)

    def snapshot(self, name):
        self.pause(.4)
        self.browser.screenshot(self.workspace / f'{name}.png')
        self.state['screenshots'].append(name)
        self.publish(message={'01-open': 'Controlled sample opened.', '02-filled': 'Synthetic inputs entered.',
                              '03-confirmed': 'Confirmation action sent; screenshot captured.'}[name])

    def watchdog(self):
        while not self.done.wait(.25):
            try:
                self.check()
            except Exception:
                # Allow ordinary teardown; force kill hung HTTP/session operations after bounded grace.
                if not self.done.wait(8):
                    if self.browser:
                        self.browser.tree.close()
                    self.publish(self.reason or 'interrupted', 'Stopped by runner watchdog; cleanup enforced.')
                    os._exit(2)
                return


def main(browser_factory=DirectWebDriver, allow_linux=False):
    workspace = Path(sys.argv[1]).resolve()
    config = json.loads((workspace / 'config.json').read_text(encoding='utf-8'))
    context = Context(workspace, config['timeout'])
    lock = None
    server = None
    threading.Thread(target=context.watchdog, daemon=True).start()
    try:
        if os.name != 'nt' and not (allow_linux and sys.platform == 'linux'):
            raise RuntimeError('WINDOWS_REQUIRED_FOR_M1A')
        lock = BrowserLock(workspace.parent / 'browser.lock')
        server, url = serve()
        context.publish(message='Starting isolated mechanical browser smoke check.')
        context.browser = browser_factory(config['chrome'], config['driver'], url,
                                         config['headed'], workspace, context.check, context.diagnostic, context.telemetry)
        context.state['browser_version'] = context.browser.version
        # Local test/supervision metadata only; API safe_snapshot never exposes process IDs.
        context.state['driver_pid'] = context.browser.process.pid
        context.publish('running', 'Robot fixture coordinates and keyboard actions; no AI or business assertions.')
        suite = TestSuite('Mechanical browser smoke')
        suite.resource.imports.library('lab.keywords.SmokeLibrary', args=[context])
        case = suite.tests.create('Server owned smoke fixture')
        for name in ('Open Controlled Sample', 'Fill Synthetic Form', 'Confirm Synthetic Order', 'Hold For Lab Inspection'):
            case.body.create_keyword(name)
        result = suite.run(output=None, log=None, report=None, console='none')
        context.check()
        outcome = 'completed' if result.return_code == 0 else 'failed'
    except BaseException as exc:
        codes = {'BROWSER_BUSY', 'PROCESS_ISOLATION_FAILED', 'DRIVER_START_FAILED',
                 'BROWSER_DRIVER_MISMATCH', 'WEBDRIVER_COMMAND_FAILED', 'WINDOWS_REQUIRED_FOR_M1A',
                 'BROWSER_SESSION_NOT_CREATED', 'BROWSER_SESSION_LOST', 'WEBDRIVER_TIMEOUT'}
        code = str(exc) if str(exc) in codes else type(exc).__name__
        # Only static exception classes/codes; no driver response, paths or tracebacks.
        if code not in codes | {'TimeoutException', 'ConnectError', 'ReadTimeout', 'PermissionError', 'FileNotFoundError', 'RuntimeError'}:
            code = 'RUNNER_INTERNAL_ERROR'
        context.state['diagnostic_code'] = code
        outcome = context.reason or 'failed'
    finally:
        context.publish('stopping', 'Closing browser and driver.')
        try:
            if context.browser:
                context.browser.close()
        except Exception:
            outcome = 'failed'
        if server:
            server.shutdown()
            server.server_close()
        shutil.rmtree(workspace / 'profile', ignore_errors=True)
        if lock:
            lock.close()
        context.publish(outcome, 'Browser smoke check completed' if outcome == 'completed'
                        else f'Browser smoke check {outcome}.')
        context.done.set()


if __name__ == '__main__':
    main()
