"""Explicit local integration harness. Uses configured CfT, never API secrets or live Mongo."""
import argparse
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.runtime import runner_environment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chrome', required=True)
    parser.add_argument('--driver', required=True)
    parser.add_argument('--case', choices=['headless', 'headed', 'cancel', 'parent-loss', 'failure', 'driver-loss', 'timeout', 'kill-runner', 'duplicate'], required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = root / '.runtime' / uuid.uuid4().hex
    path.mkdir(parents=True)
    (path / 'heartbeat').touch()
    config = {'chrome': args.chrome, 'driver': args.driver, 'headed': args.case == 'headed',
              'timeout': 2 if args.case == 'timeout' else 60}
    if args.case == 'failure':
        config['chrome'] = str(path / 'missing-chrome.exe')
    (path / 'config.json').write_text(json.dumps(config), encoding='utf-8')
    stop = threading.Event()
    def heartbeat():
        while not stop.wait(.3):
            (path / 'heartbeat').touch()
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    process = subprocess.Popen([sys.executable, '-m', 'lab.supervisor', str(path)], cwd=root,
                               env=runner_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started = time.monotonic()
    triggered = False
    second = None
    driver_pids = set()
    # Probe driver processes through Windows CIM outside runner dependency graph.
    def tree_pids():
        command = f"Get-CimInstance Win32_Process | Where-Object {{ $_.ProcessId -ne $PID -and ($_.CommandLine -like '*{path.name}*' -or $_.ParentProcessId -eq {process.pid}) }} | Select-Object -ExpandProperty ProcessId"
        value = subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True)
        return {int(line.strip()) for line in value.splitlines() if line.strip().isdigit()} - {process.pid}
    try:
        while process.poll() is None and time.monotonic() - started < 85:
            try:
                state = json.loads((path / 'state.json').read_text())
            except (OSError, ValueError):
                state = {}
            if state.get('state') == 'running' and not triggered:
                if args.case == 'driver-loss':
                    os.kill(state['driver_pid'], signal.SIGTERM)
                driver_pids = tree_pids()
                triggered = True
                if args.case == 'cancel': (path / 'cancel').touch()
                elif args.case == 'parent-loss': stop.set()
                elif args.case == 'kill-runner': process.kill()
                elif args.case == 'duplicate':
                    other = root / '.runtime' / uuid.uuid4().hex
                    other.mkdir()
                    (other / 'heartbeat').touch()
                    (other / 'config.json').write_text(json.dumps(config))
                    second = subprocess.Popen([sys.executable, '-m', 'lab.supervisor', str(other)], cwd=root,
                                              env=runner_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    second.wait(10)
                    assert json.loads((other / 'state.json').read_text())['state'] == 'failed'
            time.sleep(.2)
        process.wait(5)
        time.sleep(1)
        # All driver/profile processes observed during run must disappear after termination.
        live = tree_pids()
        assert not live, f'Orphan child processes: {live}'
        state = json.loads((path / 'state.json').read_text())
        expected = {'cancel': 'cancelled', 'parent-loss': 'interrupted', 'failure': 'failed', 'driver-loss': 'failed', 'timeout': 'timed_out'}.get(args.case, 'completed')
        if args.case != 'kill-runner':
            assert state['state'] == expected, state
            if expected == 'completed':
                assert len(state['screenshots']) == 3, state
        print(json.dumps({'case': args.case, 'state': state['state'], 'screenshots': state['screenshots'],
                          'observed_child_pids': len(driver_pids), 'cleanup': 'verified', 'workspace': str(path)}))
    finally:
        stop.set()
        if process.poll() is None:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main()
