"""Fixed local helper. Caller must establish container exit before invoking it."""
import json
import re
from pathlib import Path
import sys

from lab.runtime import atomic_json

TERMINAL = {'completed', 'failed', 'cancelled', 'interrupted', 'timed_out'}


def finalize(workspace, reason='interrupted', source='container_exit', exit_code=None):
    if reason not in {'interrupted', 'timed_out'}:
        raise ValueError('INVALID_RECONCILIATION_REASON')
    state_path = workspace / 'state.json'
    if workspace.is_symlink() or state_path.is_symlink():
        raise RuntimeError('UNSAFE_STATE_PATH')
    if state_path.exists() and state_path.stat().st_size > 1_000_000:
        raise RuntimeError('STATE_TOO_LARGE')
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    if state.get('state') in TERMINAL:
        return False
    state['state'] = reason
    state.setdefault('logs', []).append('Interrupted execution reconciled from process exit; no replay.')
    state['reconciliation'] = {'source': source, 'exit_code': exit_code, 'replayed': False}
    # Keep screenshot references and diagnostics, without claiming browser-level cleanup.
    atomic_json(state_path, state)
    return True


def main():
    if len(sys.argv) != 3 or not re.fullmatch(r'[0-9a-f]{32}', sys.argv[1]):
        raise SystemExit('INVALID_RECONCILIATION_INPUT')
    code = int(sys.argv[2])
    if not 0 <= code <= 255:
        raise SystemExit('INVALID_EXIT_CODE')
    workspace = Path('/output') / sys.argv[1]
    if not workspace.is_dir():
        raise SystemExit('MISSING_RUN_DIRECTORY')
    changed = finalize(workspace, exit_code=code)
    print(json.dumps({'changed': changed, 'replayed': False}))


if __name__ == '__main__':
    main()
