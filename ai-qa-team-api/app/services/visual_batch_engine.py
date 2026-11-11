"""Fixed local Podman adapter. No raw engine output crosses the API boundary."""
import json
import os
from pathlib import Path
import re
import subprocess
import time


class EngineError(Exception):
    def __init__(self, code, *, reason=None):
        super().__init__(code)
        # Private diagnostic category only; never retain arguments/raw engine output.
        self.reason = reason


class PodmanBatchEngine:
    def __init__(self, executable):
        if not executable or not Path(executable).is_file():
            raise EngineError('ENGINE_UNAVAILABLE')
        self.executable = str(Path(executable).resolve())

    def command(self, *args, absent=False):
        names = {'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA', 'APPDATA',
                 'PROGRAMDATA', 'USERPROFILE', 'HOME', 'PATH', 'XDG_RUNTIME_DIR'}
        env = {k: v for k, v in os.environ.items() if k.upper() in names}
        try:
            result = subprocess.run([self.executable, *args], env=env, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=30,
                **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
        except subprocess.TimeoutExpired:
            raise EngineError('ENGINE_UNAVAILABLE', reason='command_timeout') from None
        except OSError:
            raise EngineError('ENGINE_UNAVAILABLE', reason='process_launch_failed') from None
        if absent and result.returncode == 1:
            return None
        if result.returncode:
            raise EngineError('ENGINE_UNAVAILABLE', reason='command_failed')
        return result.stdout.strip()

    @staticmethod
    def name(batch_id):
        if not re.fullmatch(r'[0-9a-f]{32}', batch_id):
            raise EngineError('INVALID_BATCH_ID')
        return 'aiqa-batch-' + batch_id

    def inspect(self, batch_id, image):
        name = self.name(batch_id)
        if self.command('container', 'exists', name, absent=True) is None:
            return None
        try:
            info = json.loads(self.command('inspect', name))[0]
            if info['Config']['Labels'].get('aiqa.batch') != batch_id or info['Image'].removeprefix('sha256:') != image.removeprefix('sha256:'):
                raise EngineError('ENGINE_UNAVAILABLE')
            return {'status': info['State']['Status'], 'pid': info['State']['Pid'],
                    'exit_code': info['State']['ExitCode'], 'id': info['Id']}
        except (ValueError, KeyError, IndexError, TypeError):
            raise EngineError('ENGINE_UNAVAILABLE') from None

    def prepare(self, batch_id, image, manifest_path, progress=None):
        if not re.fullmatch(r'(sha256:)?[0-9a-f]{64}', image):
            raise EngineError('IMAGE_UNAVAILABLE')
        name = self.name(batch_id)
        steps = [('image_lookup', ('image', 'exists', image)),
            ('volume_create', ('volume', 'create', name + '-output')),
            ('container_create', ('create', '--name', name, '--label', 'aiqa.batch=' + batch_id,
            '--restart=no', '--network', 'none', '--shm-size', '512m', '--memory', '2g',
            '--cpus', '2', '--pids-limit', '256', '--mount', 'source=' + name + '-output,target=/output',
            '--entrypoint', 'python', image, '-m', 'linux.batch')),
            ('manifest_copy', ('cp', str(manifest_path), name + ':/output/manifest.json'))]
        for stage, args in steps:
            if progress:
                progress(stage, 'started', None, None)
            started = time.monotonic()
            try:
                self.command(*args)
            except EngineError as exc:
                if progress:
                    progress(stage, 'failed', round((time.monotonic()-started)*1000), exc.reason or 'unknown')
                raise
            if progress:
                progress(stage, 'completed', round((time.monotonic()-started)*1000), None)

    def start(self, batch_id):
        self.command('start', self.name(batch_id))

    def stop(self, batch_id):
        self.command('stop', '--time', '20', self.name(batch_id))

    def remove_unstarted(self, batch_id, image):
        info = self.inspect(batch_id, image)
        if info and info['status'] == 'created':
            # Remove only this owned container; retain its volume. A delayed start
            # cannot subsequently find/replay this deterministic identity.
            self.command('rm', '--force', info['id'])
        return self.inspect(batch_id, image)

    def copy(self, batch_id, source, destination):
        # Sources are constructed by trusted code, never URL/filesystem request input.
        self.command('cp', self.name(batch_id) + ':/output/' + source, str(destination))
