"""Sequential, first-attempt-only development measurements; failures stay in denominator."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.runtime import runner_environment


def run_one(root, python, chrome, driver, headed):
    path = root / '.runtime' / uuid.uuid4().hex
    path.mkdir(parents=True)
    (path / 'heartbeat').touch()
    (path / 'config.json').write_text(json.dumps({'chrome': chrome, 'driver': driver, 'headed': headed, 'timeout': 60}))
    stopped = threading.Event()
    def heartbeat():
        while not stopped.wait(.3): (path / 'heartbeat').touch()
    threading.Thread(target=heartbeat, daemon=True).start()
    started = time.monotonic()
    process = subprocess.Popen([python, '-m', 'lab.supervisor', str(path)], cwd=root,
                               env=runner_environment(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        process.wait(80)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(5)
    finally:
        stopped.set()
    elapsed = round(time.monotonic()-started, 3)
    try: state = json.loads((path / 'state.json').read_text())
    except (ValueError, OSError): state = {}
    command = f"Get-CimInstance Win32_Process | Where-Object {{ $_.ProcessId -ne $PID -and ($_.CommandLine -like '*{path.name}*' -or $_.ParentProcessId -eq {process.pid}) }} | Select-Object -ExpandProperty ProcessId"
    cleanup_deadline = time.monotonic()+5
    while True:
        probe = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True, timeout=15)
        survivors = [v for v in probe.stdout.splitlines() if v.strip().isdigit()]
        if probe.returncode or not survivors or time.monotonic() >= cleanup_deadline: break
        # Job Object termination is asynchronous; poll observed cleanup, never retry the run.
        time.sleep(.1)
    return {'run_id': path.name, 'headed': headed, 'state': state.get('state', 'missing'),
            'first_attempt_success': state.get('state') == 'completed' and len(state.get('screenshots', [])) == 3,
            'duration_seconds': elapsed, 'stage': state.get('startup_stage'),
            'reason': state.get('startup_reason'), 'code': state.get('diagnostic_code'),
            'stage_ms': state.get('startup_timings_ms', {}),
            'startup_diagnostics': state.get('startup_diagnostics'),
            'cleanup': 'no_survivors_observed' if probe.returncode == 0 and not survivors else 'failed_or_unverified',
            'survivor_count': len(survivors)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chrome', required=True)
    parser.add_argument('--driver', required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--headless', type=int, default=10)
    parser.add_argument('--headed', type=int, default=5)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    rows = []
    for headed, count in ((False, args.headless), (True, args.headed)):
        for number in range(count):
            row = run_one(root, args.python, args.chrome, args.driver, headed)
            row['number'] = number+1
            rows.append(row)
            Path(args.output).write_text(json.dumps(rows, indent=2))
            print(json.dumps(row), flush=True)
            if row['cleanup'] != 'no_survivors_observed':
                raise SystemExit('Cleanup unverified; stopped before launching another browser.')


if __name__ == '__main__': main()
