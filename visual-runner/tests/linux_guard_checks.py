"""Actual local container fault injection. Retains stopped containers and artifacts."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid

from linux_reconcile_control import reconcile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--podman', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    def call(*items, timeout=30):
        result = subprocess.run([args.podman, *items], capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError('GUARD_PROBE_OPERATION_FAILED:' + items[0])
        return result.stdout.strip()
    if call('ps', '-q'):
        raise RuntimeError('OTHER_RUNNING_CONTAINERS_PRESENT')
    image = call('image', 'inspect', 'localhost/ai-qa-m1a-linux:guard', '--format', '{{.Id}}')
    report = {'image': image, 'attempts': []}
    for mode in ['forced-reconcile', 'frozen-child-watchdog', 'completed-preserved']:
        name = 'm1a-guard-' + uuid.uuid4().hex[:12]
        volume = name + '-output'
        call('volume', 'create', volume)
        started = time.monotonic()
        call('run', '-d', '--name', name, '--label', 'aiqa.m1a.guard=true', '--restart=no',
             '--network', 'none', '--shm-size', '512m', '--memory', '2g', '--cpus', '2',
             '--pids-limit', '256', '--mount', f'source={volume},target=/output', image)
        run = None
        for _ in range(30):
            probe = "import pathlib,json; print(json.dumps([p.name for p in pathlib.Path('/output').iterdir() if p.is_dir()]))"
            runs = json.loads(call('exec', name, 'python', '-c', probe))
            if runs:
                run = runs[0]
                break
            time.sleep(.1)
        if not run or len(run) != 32 or any(c not in '0123456789abcdef' for c in run):
            raise RuntimeError('INVALID_RUN_ID')
        rejected_active = False
        try:
            reconcile(args.podman, name, run)
        except RuntimeError as exc:
            if str(exc) != 'CONTAINER_NOT_STOPPED':
                raise
            rejected_active = True
        if mode != 'completed-preserved':
            active = False
            for _ in range(20):
                probe = f"import json; print(json.load(open('/output/{run}/state.json')).get('state'))"
                if call('exec', name, 'python', '-c', probe) == 'running':
                    active = True
                    break
                time.sleep(.1)
            if not active:
                raise RuntimeError('NO_ACTIVE_SESSION_OBSERVED')
            if mode == 'forced-reconcile':
                call('kill', '--signal', 'KILL', name)
            else:
                # Freeze only the task supervisor, including its own watchdog.
                # The unmodified parent must enforce its actual 100s+10s deadline.
                probe = "import os,pathlib,signal; pids=[int(p.parent.name) for p in pathlib.Path('/proc').glob('[0-9]*/cmdline') if b'linux.entrypoint' in p.read_bytes().split(b'\\0') and b'--child' in p.read_bytes().split(b'\\0')]; assert len(pids)==1; os.kill(pids[0],signal.SIGSTOP); print('child_frozen')"
                if call('exec', name, 'python', '-c', probe) != 'child_frozen':
                    raise RuntimeError('FAULT_NOT_INJECTED')
        call('wait', name, timeout=125)
        stopped_seconds = round(time.monotonic()-started, 3)
        info = json.loads(call('inspect', name))[0]
        if info['State']['Status'] != 'exited' or info['State']['Pid'] != 0:
            raise RuntimeError('CONTAINER_NOT_EXITED')
        folder = args.output / mode
        folder.mkdir()
        def state_copy(filename):
            path = folder / filename
            call('cp', name + ':/output/' + run + '/state.json', str(path.resolve()))
            return path.read_bytes()
        before = state_copy('before.json')
        first = reconcile(args.podman, name, run)
        after = state_copy('after.json')
        second = reconcile(args.podman, name, run)
        again = state_copy('again.json')
        state = json.loads(after)
        expected = {'forced-reconcile': 'interrupted', 'frozen-child-watchdog': 'timed_out',
                    'completed-preserved': 'completed'}[mode]
        item = {'case': mode, 'container': name, 'run': run, 'container_exit_seconds': stopped_seconds,
                'exit_code': info['State']['ExitCode'], 'pid': info['State']['Pid'],
                'oom_killed': info['State']['OOMKilled'], 'state_before': json.loads(before).get('state'),
                'state_after': state.get('state'), 'active_reconcile_rejected': rejected_active,
                'first_reconcile': first, 'second_reconcile': second,
                'idempotent': after == again, 'terminal_preserved': before == after,
                'screenshots': state.get('screenshots', [])}
        item['passed'] = state.get('state') == expected and rejected_active and after == again and not info['State']['OOMKilled'] and (
            first['changed'] if mode == 'forced-reconcile' else before == after)
        report['attempts'].append(item)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(item), flush=True)
        if call('ps', '-q'):
            raise RuntimeError('CONTAINERS_REMAIN_RUNNING')


if __name__ == '__main__':
    main()
