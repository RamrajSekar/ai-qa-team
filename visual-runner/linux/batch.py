"""Fixed synthetic batch entrypoint; one isolated supervisor/session at a time."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

from lab.runtime import atomic_json
from linux.contract_validation import validate_manifest


def stamp():
    return datetime.now(timezone.utc).isoformat()


def cleanup_outcome(outcome, remaining):
    # Cancellation/timeout already end the container. Remnants must prevent a
    # subsequent case, but must not relabel a deliberately cancelled execution.
    return 'interrupted' if remaining and outcome in {'completed', 'failed'} else outcome


def browsers_remaining():
    for status in Path('/proc').glob('[0-9]*/status'):
        try:
            fields = dict(line.split(':', 1) for line in status.read_text().splitlines() if ':' in line)
            if fields.get('Name', '').strip() in {'chrome', 'chromedriver', 'chrome_crashpad'} and not fields.get('State', '').strip().startswith('Z'):
                return True
        except FileNotFoundError:
            pass
    return False


def main():
    if sys.platform != 'linux' or os.geteuid() == 0 or len(sys.argv) != 1:
        raise SystemExit('FIXED_NON_ROOT_LINUX_BATCH_REQUIRED')
    os.umask(0o077)
    root = Path('/output')
    path = root / 'batch-state.json'
    # Never resume/replay an existing batch, including completed cases.
    if path.exists():
        raise SystemExit('BATCH_ALREADY_STARTED')
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    validate_manifest(manifest)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    state = {'schema_version': '1.0', 'batch_id': manifest['batch_id'], 'state': 'running',
             'cases': [{'case_run_id': c['case_run_id'], 'state': 'queued', 'screenshots': []} for c in manifest['cases']]}
    atomic_json(path, state)
    batch_started = time.monotonic()
    final = 'completed'
    for case in state['cases']:
        if stop.is_set() or time.monotonic() - batch_started > manifest['batch_timeout_seconds']:
            final = 'cancelled' if stop.is_set() else 'timed_out'
            break
        workspace = root / 'cases' / case['case_run_id']
        workspace.mkdir(parents=True, exist_ok=False)
        atomic_json(workspace / 'config.json', {'chrome': '/opt/cft/chrome-linux64/chrome',
            'driver': '/opt/cft/chromedriver-linux64/chromedriver', 'headed': False, 'timeout': 90})
        heartbeat = workspace / 'heartbeat'
        heartbeat.touch()
        case.update(state='starting', started_at=stamp())
        atomic_json(path, state)
        process = subprocess.Popen([sys.executable, '-m', 'linux.entrypoint', '--child', str(workspace)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        started = time.monotonic()
        stopping_at = None
        forced = False
        while process.poll() is None:
            heartbeat.touch()
            if stop.is_set() or time.monotonic() - batch_started > manifest['batch_timeout_seconds'] or time.monotonic()-started > 100:
                (workspace / 'cancel').touch()
                stopping_at = stopping_at or time.monotonic()
                if time.monotonic() - stopping_at > 10:
                    process.kill()
                    process.wait(timeout=5)
                    forced = True
                    break
            try:
                raw = json.loads((workspace / 'state.json').read_text(encoding='utf-8'))
                if raw.get('state') in {'starting', 'running', 'stopping'}:
                    case['state'] = raw['state']
                case['screenshots'] = [v for v in raw.get('screenshots', []) if v in {'01-open', '02-filled', '03-confirmed'}]
                atomic_json(path, state)
            except (OSError, ValueError):
                pass
            time.sleep(.25)
        try:
            raw = json.loads((workspace / 'state.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raw = {}
        case['screenshots'] = [v for v in raw.get('screenshots', []) if v in {'01-open', '02-filled', '03-confirmed'}]
        outcome = raw.get('state')
        if outcome not in {'completed', 'failed', 'cancelled', 'interrupted', 'timed_out'}:
            outcome = 'cancelled' if stop.is_set() else 'timed_out' if forced else 'interrupted'
        case.update(state=outcome, finished_at=stamp())
        cleanup_deadline = time.monotonic() + 2
        while browsers_remaining() and time.monotonic() < cleanup_deadline:
            time.sleep(.1)
        outcome = cleanup_outcome(outcome, browsers_remaining())
        case['state'] = outcome
        # API independently sanitizes per-case diagnostic IPC and privately copies PNGs.
        atomic_json(path, state)
        if forced or outcome in {'cancelled', 'interrupted', 'timed_out'}:
            final = outcome
            break  # A hung supervisor may leave browser children; exit the container now.
        if outcome == 'failed':
            final = 'failed'
    for case in state['cases']:
        if case['state'] == 'queued':
            case['state'] = 'cancelled' if final == 'cancelled' else 'not_executed'
    state['state'] = final
    atomic_json(path, state)
    print('Browser smoke check completed' if final == 'completed' else 'Browser smoke check incomplete', flush=True)
    raise SystemExit(0 if final == 'completed' else 1)


if __name__ == '__main__':
    main()
