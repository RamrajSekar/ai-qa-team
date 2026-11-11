"""Local Podman control, never an API endpoint or multi-host reconciler."""
import argparse
import json
import re
import subprocess
import uuid


def reconcile(podman, container, run):
    if not re.fullmatch(r'm1a-guard-[0-9a-f]{12}', container) or not re.fullmatch(r'[0-9a-f]{32}', run):
        raise RuntimeError('INVALID_LOCAL_RUN_IDENTITY')
    def call(*args):
        result = subprocess.run([podman, *args], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError('LOCAL_RECONCILIATION_OPERATION_FAILED')
        return result.stdout.strip()
    info = json.loads(call('inspect', container))[0]
    if info.get('Config', {}).get('Labels', {}).get('aiqa.m1a.guard') != 'true':
        raise RuntimeError('UNMANAGED_CONTAINER')
    if info['State']['Status'] != 'exited' or info['State']['Running'] or info['State']['Pid'] != 0:
        raise RuntimeError('CONTAINER_NOT_STOPPED')
    mounts = [m for m in info['Mounts'] if m['Destination'] == '/output' and m['Type'] == 'volume']
    if len(mounts) != 1 or mounts[0]['Name'] != container + '-output':
        raise RuntimeError('OUTPUT_IDENTITY_MISMATCH')
    # Fixed helper from exactly the original image, not a newer mutable tag.
    helper = container + '-reconcile-' + uuid.uuid4().hex[:6]
    raw = call('run', '--rm', '--name', helper, '--label', 'aiqa.m1a.helper=true',
               '--network', 'none', '--memory', '128m', '--cpus', '1', '--pids-limit', '32',
               '--mount', 'source=' + mounts[0]['Name'] + ',target=/output',
               '--entrypoint', 'python', info['Image'], '-m', 'linux.reconcile', run,
               str(info['State']['ExitCode']))
    return json.loads(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--podman', required=True)
    parser.add_argument('--container', required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    print(json.dumps(reconcile(args.podman, args.container, args.run)))
