"""Development-only isolated smoke runner. Never submits legacy execution jobs."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import uuid

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.db.connection import db
from app.models.visual_lab_model import VisualLabRun
from app.utils.feature_flags import require_features

ROOT = Path(__file__).resolve().parents[3] / 'visual-runner'
ARTIFACTS = {'01-open', '02-filled', '03-confirmed'}
ACTIVE = ['starting', 'running', 'stopping']
TERMINAL = ['completed', 'failed', 'cancelled', 'interrupted', 'timed_out']
STAGES = {'driver_version', 'driver_launch', 'driver_readiness', 'session_creation', 'browser_launch', 'devtools_connect', 'session_handshake', 'version_validation', 'session_timeouts', 'ready', 'navigation', 'navigation_checkpoint', 'screenshot'}
REASONS = {'browser_exited', 'devtools_port_missing', 'profile_in_use', 'browser_unreachable', 'browser_disconnected'}
DIAGNOSTICS = {'BROWSER_BUSY', 'PROCESS_ISOLATION_FAILED', 'DRIVER_START_FAILED',
    'BROWSER_SESSION_NOT_CREATED', 'BROWSER_SESSION_LOST', 'WEBDRIVER_TIMEOUT',
    'BROWSER_DRIVER_MISMATCH', 'WEBDRIVER_COMMAND_FAILED', 'WINDOWS_REQUIRED_FOR_M1A',
    'TimeoutException', 'ConnectError', 'ReadTimeout', 'PermissionError', 'FileNotFoundError',
    'RuntimeError', 'RUNNER_INTERNAL_ERROR'}
SAFE_LOGS = {
    'Starting isolated mechanical browser smoke check.', 'Controlled sample opened.',
    'Synthetic inputs entered.', 'Confirmation action sent; screenshot captured.',
    'Robot fixture coordinates and keyboard actions; no AI or business assertions.',
    'Closing browser and driver.', 'Stopped by runner watchdog; cleanup enforced.',
    'Browser smoke check completed', 'Runner exited unexpectedly.', 'Runner configuration unavailable.',
    'Browser smoke check failed.', 'Browser smoke check cancelled.', 'Browser smoke check interrupted.',
    'Browser smoke check timed_out.', 'Backend supervision stopped.',
}


def now():
    return datetime.now(timezone.utc)


def guard():
    require_features('visual_runner_lab')
    if settings.app_env.strip().lower() not in {'development', 'local', 'test'}:
        raise HTTPException(403, 'Visual Runner Lab is available only in development.')


def workspace(run_id):
    if not re.fullmatch(r'[0-9a-f]{32}', run_id):
        raise HTTPException(404, 'Smoke check not found')
    return ROOT / '.runtime' / run_id


def safe_snapshot(path):
    try:
        raw = json.loads((path / 'state.json').read_text(encoding='utf-8'))
        state = raw.get('state')
        if state not in ACTIVE + TERMINAL:
            return None
        version = raw.get('browser_version')
        return {'state': state, 'logs': [v for v in raw.get('logs', []) if v in SAFE_LOGS][-40:],
                'startup_stage': raw.get('startup_stage') if raw.get('startup_stage') in STAGES else None,
                'startup_reason': raw.get('startup_reason') if raw.get('startup_reason') in REASONS else None,
                'startup_timings_ms': {k: v for k, v in raw.get('startup_timings_ms', {}).items()
                                       if k in STAGES and type(v) is int and 0 <= v <= 120000},
                'screenshots': [v for v in raw.get('screenshots', []) if v in ARTIFACTS],
                'startup_diagnostics': safe_startup_diagnostics(raw.get('startup_diagnostics')),
                'diagnostic_code': raw.get('diagnostic_code') if raw.get('diagnostic_code') in DIAGNOSTICS else None,
                'browser_version': version if isinstance(version, str) and re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version) else None}
    except (OSError, ValueError, TypeError):
        return None


def safe_startup_diagnostics(raw):
    if not isinstance(raw, dict):
        return None
    safe = {}
    enums = {'driver_state': {'not_started', 'running', 'exited', 'unknown'},
             'browser_state': {'running', 'exited', 'not_observed', 'unavailable'},
             'cleanup_browser_state': {'running', 'exited', 'not_observed', 'unavailable'},
             'devtools_port_file': {'present', 'absent', 'unavailable'},
             'cleanup': {'not_started', 'driver_exited_job_closed', 'unverified'}}
    for key, allowed in enums.items():
        if isinstance(raw.get(key), str) and raw[key] in allowed:
            safe[key] = raw[key]
    version = raw.get('driver_version')
    if isinstance(version, str) and re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,6}\.\d{1,6}', version):
        safe['driver_version'] = version
    for key in ('driver_exit_code', 'cleanup_driver_exit_code'):
        if type(raw.get(key)) is int and -2147483648 <= raw[key] <= 4294967295:
            safe[key] = raw[key]
    if type(raw.get('session_created')) is bool:
        safe['session_created'] = raw['session_created']
    values = raw.get('native_errors')
    if isinstance(values, list):
        safe['native_errors'] = sorted({v for v in values[:32] if isinstance(v, str)
            and v in {'access_denied', 'devtools_port_missing', 'browser_exited', 'profile_in_use'}})
    return safe


class VisualLabService:
    def __init__(self):
        self.tasks = set()
        self.processes = {}
        self.lock_id = f'visual-smoke:{socket.gethostname()}'

    async def start(self, project_id, user, headed):
        guard()
        if settings.features.visual_runner_batches:
            raise HTTPException(409, 'Linux batch mode owns development capacity; use the batch API or disable its flag.')
        # Feature-off is not evidence that bounded containers have stopped.
        # Hold local Windows starts until both durable Linux ledgers are empty.
        for identity in ['local-linux-batch-v1', 'local-linux-check-pool-v1']:
            ledger = await db['visual_batch_dispatch'].find_one({'_id': identity})
            if ledger and any(ledger.get('slots', {}).values()):
                raise HTTPException(409, 'Linux execution is still reconciling; wait for capacity release.')
        python = Path(settings.visual_runner_python) if settings.visual_runner_python else ROOT / '.venv' / 'Scripts' / 'python.exe'
        chrome, driver = settings.visual_runner_chrome, settings.visual_runner_driver
        if os.name != 'nt' or not python.is_file() or not chrome or not driver or not Path(chrome).is_file() or not Path(driver).is_file():
            raise HTTPException(503, 'Configure the isolated Windows runner, Chrome for Testing and matched ChromeDriver. See M1A setup.')
        run_id = uuid.uuid4().hex
        # Atomic singleton reservation across API processes sharing this local Mongo database.
        try:
            lease = await db['visual_lab_locks'].find_one_and_update(
                {'_id': self.lock_id, '$or': [{'expires_at': {'$lt': now()}}, {'run_id': None}]},
                {'$set': {'run_id': run_id, 'expires_at': now() + timedelta(seconds=20)}},
                upsert=True, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            raise HTTPException(409, 'A local browser smoke check is already active.') from None
        if not lease:
            raise HTTPException(409, 'A local browser smoke check is already active.')
        path = workspace(run_id)
        process = None
        try:
            path.mkdir(parents=True, exist_ok=False)
            (path / 'heartbeat').touch()
            (path / 'config.json').write_text(json.dumps({'chrome': str(Path(chrome).resolve()),
                'driver': str(Path(driver).resolve()), 'headed': headed,
                'timeout': settings.visual_runner_timeout_seconds}), encoding='utf-8')
            doc = VisualLabRun(run_id=run_id, project_id=project_id, headed=headed, state='starting',
                               created_at=now().isoformat(), updated_at=now().isoformat()).model_dump()
            # Private ownership/host fields are never part of response models.
            await db['visual_lab_runs'].insert_one({**doc, 'created_by': user['email'], 'host_id': self.lock_id})
            # Deliberately do not inherit API/database/provider secrets, proxy or PYTHONPATH.
            env = {key: value for key, value in os.environ.items()
                   if key.upper() in {'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA',
                                      'APPDATA', 'PROGRAMDATA', 'COMSPEC', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
                                      'PROGRAMW6432', 'USERPROFILE', 'PATH'}}
            env['PYTHONUTF8'] = '1'
            process = subprocess.Popen([str(python), '-m', 'lab.supervisor', str(path)], cwd=ROOT,
                env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self.processes[run_id] = process
            task = asyncio.create_task(self.monitor(run_id, project_id, path, process))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            return VisualLabRun(**doc)
        except Exception:
            if process:
                (path / 'cancel').touch()
            await db['visual_lab_runs'].update_one({'run_id': run_id, 'project_id': project_id},
                {'$set': {'state': 'failed', 'logs': ['Runner configuration unavailable.'], 'updated_at': now().isoformat()}})
            await self.release(run_id)
            raise HTTPException(503, 'The isolated smoke runner could not start.') from None

    async def release(self, run_id):
        await db['visual_lab_locks'].update_one({'_id': self.lock_id, 'run_id': run_id},
                                              {'$set': {'run_id': None, 'expires_at': now()}})

    async def monitor(self, run_id, project_id, path, process):
        deadline = time.monotonic() + settings.visual_runner_timeout_seconds + 20
        try:
            while process.poll() is None:
                if time.monotonic() > deadline:
                    (path / 'cancel').touch()
                    # Supervisor has its own watchdog; stop heartbeat and allow it to kill its Job Object.
                    break
                if not settings.features.visual_runner_lab:
                    (path / 'cancel').touch()
                (path / 'heartbeat').touch()
                await db['visual_lab_locks'].update_one({'_id': self.lock_id, 'run_id': run_id},
                    {'$set': {'expires_at': now() + timedelta(seconds=20)}})
                await self.reconcile(run_id, project_id)
                await asyncio.sleep(.5)
            if process.poll() is None:
                await asyncio.to_thread(process.wait, 18)
        except (Exception, asyncio.CancelledError):
            (path / 'cancel').touch()
            # A DB outage also stops heartbeat: no browser can run indefinitely without supervision.
            try:
                await asyncio.to_thread(process.wait, 18)
            except subprocess.TimeoutExpired:
                process.kill()  # Closing supervisor handle kills driver/browser through Job Object.
                await asyncio.to_thread(process.wait, 5)
        finally:
            self.processes.pop(run_id, None)
            try:
                await self.reconcile(run_id, project_id, exited=True)
                await self.release(run_id)
            except Exception:
                pass  # Durable lease expires; next authorized status/list reconciles run file state.

    async def reconcile(self, run_id, project_id, exited=False):
        doc = await db['visual_lab_runs'].find_one({'run_id': run_id, 'project_id': project_id})
        if not doc:
            raise HTTPException(404, 'Smoke check not found')
        if doc['state'] not in ACTIVE or doc['host_id'] != self.lock_id:
            return VisualLabRun(**doc)
        path = workspace(run_id)
        snapshot = safe_snapshot(path)
        if snapshot and snapshot['state'] in TERMINAL:
            update = snapshot
        elif exited:
            update = {'state': 'interrupted', 'logs': ['Runner exited unexpectedly.']}
        else:
            try:
                stale = time.time() - (path / 'heartbeat').stat().st_mtime > 22
            except OSError:
                stale = True
            update = {'state': 'interrupted', 'logs': ['Backend supervision stopped.']} if stale else snapshot
        if update and update['state'] in ACTIVE and (path / 'cancel').exists():
            update['state'] = 'stopping'
        if update:
            update['updated_at'] = now().isoformat()
            await db['visual_lab_runs'].update_one({'run_id': run_id, 'project_id': project_id, 'state': {'$in': ACTIVE}}, {'$set': update})
            doc.update(update)
        return VisualLabRun(**doc)

    async def cancel(self, run_id, project_id):
        guard()
        run = await self.reconcile(run_id, project_id)
        if run.state in ACTIVE:
            local = await db['visual_lab_runs'].find_one({'run_id': run_id, 'project_id': project_id, 'host_id': self.lock_id})
            if not local:
                raise HTTPException(409, 'This smoke check belongs to another development host.')
            (workspace(run_id) / 'cancel').touch()
            await db['visual_lab_runs'].update_one({'run_id': run_id, 'project_id': project_id, 'state': {'$in': ACTIVE}},
                                                 {'$set': {'state': 'stopping', 'updated_at': now().isoformat()}})
        return await self.reconcile(run_id, project_id)

    async def shutdown(self):
        for run_id in list(self.processes):
            (workspace(run_id) / 'cancel').touch()
        if self.tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*list(self.tasks), return_exceptions=True), timeout=20)
            except asyncio.TimeoutError:
                pass

    async def recover(self):
        """Reconcile old host-local records without restarting or replaying any run."""
        await asyncio.sleep(23)  # Old supervisors have already exhausted heartbeat + teardown grace.
        docs = await db['visual_lab_runs'].find({'host_id': self.lock_id, 'state': {'$in': ACTIVE}}).limit(100).to_list(100)
        for doc in docs:
            await self.reconcile(doc['run_id'], doc['project_id'])


visual_lab = VisualLabService()
