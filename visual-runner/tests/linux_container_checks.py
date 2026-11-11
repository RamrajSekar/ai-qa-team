"""Opt-in real Podman checks, fixed synthetic image only; no API integration."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid


TIMEOUT_PROBE = '''
import functools,json,sys,threading,time
from pathlib import Path
from lab.runtime import atomic_json
from lab.supervisor import main
from lab.webdriver import DirectWebDriver
from linux.process_tree import LinuxProcessTree
w=Path('/output/timeout-probe');w.mkdir()
atomic_json(w/'config.json',{'chrome':'/opt/cft/chrome-linux64/chrome','driver':'/opt/cft/chromedriver-linux64/chromedriver','headed':False,'timeout':2})
def beat():
 while True:
  (w/'heartbeat').touch();time.sleep(.2)
(w/'heartbeat').touch()
threading.Thread(target=beat,daemon=True).start()
sys.argv=['probe',str(w)]
main(browser_factory=functools.partial(DirectWebDriver,tree_factory=LinuxProcessTree),allow_linux=True)
state=json.loads((w/'state.json').read_text())
sys.exit(0 if state.get('state')=='completed' else 1)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--podman', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--recover-forced', help='Collect an already stopped task-owned forced-stop attempt; do not replay it')
    parser.add_argument('--recover-run')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    def call(*items, timeout=30):
        result = subprocess.run([args.podman, *items], capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError('PODMAN_OPERATION_FAILED:' + items[0])
        return result.stdout.strip()
    image = 'localhost/ai-qa-m1a-linux:local'
    report = {'image': call('image', 'inspect', image, '--format', '{{.Id}}'), 'attempts': []}
    # Refuse concurrent containers rather than interfere with unrelated work.
    if call('ps', '-q'):
        raise RuntimeError('RUNNING_CONTAINERS_PRESENT')
    for mode in ['forced-stop', 'timeout', 'baseline-1', 'baseline-2', 'baseline-3']:
        recovered = mode == 'forced-stop' and args.recover_forced is not None
        name = args.recover_forced if recovered else 'm1a-verify-' + uuid.uuid4().hex[:12]
        volume = name + '-output'
        if not recovered:
            call('volume', 'create', volume)
        command = ['run', '-d', '--name', name, '--network', 'none', '--shm-size', '512m',
                   '--memory', '2g', '--cpus', '2', '--pids-limit', '256',
                   '--mount', f'source={volume},target=/output']
        if mode == 'timeout':
            command += ['--entrypoint', 'python', image, '-c', TIMEOUT_PROBE]
        else:
            command += [image]
        started = time.monotonic()
        if not recovered:
            call(*command)
        run = args.recover_run if recovered else 'timeout-probe' if mode == 'timeout' else None
        if run is None:
            for _ in range(20):
                probe = "import pathlib,json; print(json.dumps([p.name for p in pathlib.Path('/output').iterdir() if p.is_dir()]))"
                runs = json.loads(call('exec', name, 'python', '-c', probe))
                if runs:
                    run = runs[0]
                    break
                time.sleep(.1)
        if run != 'timeout-probe' and (not run or len(run) != 32 or any(c not in '0123456789abcdef' for c in run)):
            raise RuntimeError('INVALID_RUN_DIRECTORY')
        observed_active = False
        if mode == 'forced-stop' and not recovered:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                # Observe a session-created running state before SIGKILL.
                probe = "import pathlib,json; print(any(json.loads(p.read_text()).get('state')=='running' for p in pathlib.Path('/output').glob('*/state.json')))"
                if call('exec', name, 'python', '-c', probe) == 'True':
                    observed_active = True
                    break
                time.sleep(.2)
            call('kill', '--signal', 'KILL', name)
        call('wait', name, timeout=120)
        info = json.loads(call('inspect', name))[0]
        folder = args.output / mode
        folder.mkdir()
        # Never copy interrupted browser profiles/symlinks onto Windows.
        target = folder / run
        target.mkdir()
        call('cp', name + ':/output/' + run + '/state.json', str((target / 'state.json').resolve()))
        saved = json.loads((target / 'state.json').read_text())
        for screenshot in saved.get('screenshots', []):
            if screenshot not in {'01-open', '02-filled', '03-confirmed'}:
                raise RuntimeError('INVALID_ARTIFACT_ID')
            call('cp', name + ':/output/' + run + '/' + screenshot + '.png', str((target / (screenshot + '.png')).resolve()))
        states = [json.loads(p.read_text()) for p in folder.glob('*/state.json')]
        state = states[0] if len(states) == 1 else {}
        if recovered:
            observed_active = state.get('state') == 'running'
        pngs = list(folder.glob('*/*.png'))
        item = {'case': mode, 'container': name, 'elapsed_seconds': None if recovered else round(time.monotonic()-started, 3),
                'recovered_artifacts_after_windows_symlink_copy_error': bool(recovered),
                'status': info['State']['Status'], 'exit_code': info['State']['ExitCode'],
                'oom_killed': info['State']['OOMKilled'], 'state': state.get('state'),
                'screenshot_count': len(pngs), 'diagnostic_code': state.get('diagnostic_code'),
                'startup_stage': state.get('startup_stage'), 'observed_active_before_kill': observed_active,
                'container_stopped': info['State']['Status'] == 'exited'}
        item['passed'] = item['container_stopped'] and not item['oom_killed'] and (
            observed_active and item['exit_code'] == 137 if mode == 'forced-stop' else
            state.get('state') == 'timed_out' if mode == 'timeout' else
            state.get('state') == 'completed' and item['exit_code'] == 0 and len(pngs) == 3)
        report['attempts'].append(item)
        (args.output / 'summary.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(item), flush=True)
        # Keep stopped containers/volumes for diagnosis. Never replay a failed attempt.
        if call('ps', '-q'):
            raise RuntimeError('CONTAINER_STILL_RUNNING')


if __name__ == '__main__':
    main()
