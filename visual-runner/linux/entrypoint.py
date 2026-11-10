"""Fixed, headless synthetic spike. No URLs/configuration supplied by callers."""
import functools
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

from lab.runtime import atomic_json
from linux.reconcile import finalize


def child():
    from lab.supervisor import main
    from lab.webdriver import DirectWebDriver
    from linux.process_tree import LinuxProcessTree
    main(browser_factory=functools.partial(DirectWebDriver, tree_factory=LinuxProcessTree), allow_linux=True)


def main():
    if sys.platform != 'linux' or os.geteuid() == 0:
        raise SystemExit('NON_ROOT_LINUX_CONTAINER_REQUIRED')
    if len(sys.argv) == 3 and sys.argv[1] == '--child':
        sys.argv = [sys.argv[0], sys.argv[2]]
        child()
        return
    if len(sys.argv) != 1:
        raise SystemExit('NO_CALLER_ARGUMENTS_ALLOWED')
    os.umask(0o077)
    workspace = Path('/output') / uuid.uuid4().hex
    workspace.mkdir()
    atomic_json(workspace / 'config.json', {
        'chrome': '/opt/cft/chrome-linux64/chrome',
        'driver': '/opt/cft/chromedriver-linux64/chromedriver',
        'headed': False, 'timeout': 90})
    heartbeat = workspace / 'heartbeat'
    heartbeat.touch()
    stopping = threading.Event()
    def cancel(*_):
        (workspace / 'cancel').touch()
        stopping.set()
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    process = subprocess.Popen([sys.executable, '-m', 'linux.entrypoint', '--child', str(workspace)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started = time.monotonic()
    cancel_started = None
    outer_expired = False
    while process.poll() is None:
        heartbeat.touch()
        if stopping.is_set() or time.monotonic() - started > 100:
            outer_expired = outer_expired or time.monotonic() - started > 100
            cancel()
            cancel_started = cancel_started or time.monotonic()
            if time.monotonic() - cancel_started > 10:
                process.kill()
                process.wait(timeout=5)
                break
        time.sleep(.25)
    finalize(workspace, reason='timed_out' if outer_expired else 'interrupted',
             source='entrypoint_watchdog' if outer_expired else 'child_exit', exit_code=process.returncode)
    state = json.loads((workspace / 'state.json').read_text(encoding='utf-8'))
    print('Browser smoke check completed' if state.get('state') == 'completed' else 'Browser smoke check incomplete', flush=True)
    raise SystemExit(0 if state.get('state') == 'completed' else 1)


if __name__ == '__main__':
    main()
