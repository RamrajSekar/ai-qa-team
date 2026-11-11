"""Development-only durable check pool with compatible legacy batch draining."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import shutil
import uuid
import time

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.db.connection import db
from app.models.visual_batch_model import BatchManifest, BatchRun, BatchStart, CaseResult, FixtureCase, CheckDispatch, PreparationDiagnostics, PreparationEvent
from app.services.visual_lab_service import ARTIFACTS, ACTIVE as OLD_ACTIVE, safe_snapshot
from app.services.visual_batch_engine import EngineError, PodmanBatchEngine
from app.utils.feature_flags import require_features

ROOT = Path(__file__).resolve().parents[3] / 'visual-runner' / '.batch-runtime'
ACTIVE = ['starting', 'running', 'stopping']
TERMINAL = ['completed', 'failed', 'cancelled', 'interrupted', 'timed_out']
LEDGER = 'local-linux-batch-v1'


def now():
    return datetime.now(timezone.utc)


def guard():
    require_features('visual_runner_lab', 'visual_runner_batches')
    if settings.app_env.lower().strip() not in {'test', 'local', 'development'}:
        raise HTTPException(403, 'Visual batches are development-only.')


def local_path(batch_id):
    if not re.fullmatch(r'[0-9a-f]{32}', batch_id):
        raise HTTPException(404, 'Batch not found')
    path = ROOT / batch_id
    if path.is_symlink() or path.resolve().parent != ROOT.resolve():
        raise HTTPException(404, 'Batch not found')
    return path


def public(doc):
    fields = BatchRun.model_fields
    run = BatchRun(**{k: v for k, v in doc.items() if k in fields})
    # Read-only compatibility for old records: use retained sanitized local IPC,
    # never contact the engine, mutate history, or replay a completed/failed case.
    for index, case in enumerate(run.cases):
        if case.startup_stage is None and case.state not in {'queued', 'not_executed'}:
            folder = local_path(run.batch_id) / case.case_run_id
            if folder.is_symlink() or (folder / 'state.json').is_symlink():
                continue
            snap = safe_snapshot(folder)
            if snap:
                run.cases[index] = CaseResult(**{**case.model_dump(), **startup_fields(snap)})
    return run


def startup_fields(snapshot):
    return {key: snapshot.get(key) for key in ('startup_stage', 'startup_reason', 'startup_diagnostics')} | {
        'startup_timings_ms': snapshot.get('startup_timings_ms', {})}


class VisualBatchService:
    def __init__(self, database=None, engine=None, host=None, *, collection="visual_batches", ledger=LEDGER, slots=2, strategy="sequential-batch-v1"):
        self.db = database if database is not None else db
        self.engine_override = engine
        self.host = host or socket.gethostname()
        self.collection, self.ledger, self.slot_count = collection, ledger, slots
        self.strategy = strategy
        self.launch_enabled = True
        self.stopping = False
        self.task = None
        self.last_error = None

    def engine(self):
        return self.engine_override or PodmanBatchEngine(settings.visual_batch_podman)

    async def initialize(self):
        await self.db[self.collection].create_index([('project_id', 1), ('created_at', -1)])
        await self.db[self.collection].create_index([('host_id', 1), ('state', 1), ('created_at', 1)])
        await self.db['visual_batch_dispatch'].update_one({'_id': self.ledger}, {'$setOnInsert': {
            'host_id': self.host, 'slots': {str(i): None for i in range(self.slot_count)}, 'last_account': None, 'last_project': None}}, upsert=True)
        ledger = await self.db['visual_batch_dispatch'].find_one({'_id': self.ledger})
        if ledger['host_id'] != self.host:
            raise EngineError('BATCH_CONFIGURATION_UNAVAILABLE')

    async def enqueue(self, project_id, user, owner, payload: BatchStart):
        guard()
        image = settings.visual_batch_image or ''
        if not re.fullmatch(r'(sha256:)?[0-9a-f]{64}', image) or not settings.visual_batch_podman:
            raise HTTPException(503, 'Configure the local batch engine and immutable image ID.')
        await self.initialize()
        # Built-in _id uniqueness atomically deduplicates requests; no transaction needed.
        key = hashlib.sha256((project_id + '\0' + user['email'].lower() + '\0' + payload.idempotency_key).encode()).hexdigest()
        batch_id = uuid.uuid4().hex
        manifest = BatchManifest(batch_id=batch_id, cases=[FixtureCase(case_run_id=uuid.uuid4().hex)
            for _ in range(payload.case_count)], batch_timeout_seconds=payload.case_count * 110)
        timestamp = now()
        run = BatchRun(batch_id=batch_id, project_id=project_id, state='queued', manifest=manifest,
            execution_strategy=self.strategy, adapter=('robot-direct-webdriver-check-pool-v1' if self.strategy == 'parallel-checks-v1' else 'robot-direct-webdriver-batch-v1'),
            cases=[CaseResult(case_run_id=c.case_run_id) for c in manifest.cases], created_at=timestamp, updated_at=timestamp)
        doc = {**run.model_dump(mode='json'), '_id': key, 'account_id': owner.lower(),
            'host_id': self.host, 'image_id': image, 'created_by': user['email'].lower(),
            'cancel_requested': False, 'start_intent': False}
        try:
            await self.db[self.collection].insert_one(doc)
        except DuplicateKeyError:
            existing = await self.db[self.collection].find_one({'_id': key, 'project_id': project_id})
            if not existing or len(existing['manifest']['cases']) != payload.case_count:
                raise HTTPException(409, 'Idempotency key already used with different input.') from None
            return public(existing)
        return public(doc)

    async def get(self, project_id, batch_id):
        guard()
        local_path(batch_id)
        doc = await self.db[self.collection].find_one({'batch_id': batch_id, 'project_id': project_id})
        if not doc:
            raise HTTPException(404, 'Batch not found')
        return public(doc)

    async def cancel(self, project_id, batch_id):
        await self.get(project_id, batch_id)
        doc = await self.db[self.collection].find_one_and_update(
            {'batch_id': batch_id, 'project_id': project_id, 'state': 'queued'},
            {'$set': {'cancel_requested': True, 'state': 'cancelled', 'updated_at': now().isoformat()}},
            return_document=ReturnDocument.AFTER)
        if doc:
            cases = [{**c, 'state': 'cancelled'} for c in doc['cases']]
            await self.db[self.collection].update_one({'_id': doc['_id'], 'state': 'cancelled'}, {'$set': {'cases': cases}})
        else:
            await self.db[self.collection].update_one({'batch_id': batch_id, 'project_id': project_id,
                'state': {'$in': ACTIVE}}, {'$set': {'cancel_requested': True, 'state': 'stopping', 'updated_at': now().isoformat()}})
        return await self.get(project_id, batch_id)

    async def save(self, doc, fields):
        return await self.db[self.collection].update_one({'_id': doc['_id'], 'state': {'$in': ACTIVE}},
            {'$set': {**fields, 'updated_at': now().isoformat()}})

    async def collect(self, doc, engine):
        path = local_path(doc['batch_id'])
        path.mkdir(parents=True, exist_ok=True)
        try:
            await asyncio.to_thread(engine.copy, doc['batch_id'], 'batch-state.json', path / 'batch-state.json')
            raw_path = path / 'batch-state.json'
            if raw_path.is_symlink() or raw_path.stat().st_size > 100000:
                return None
            raw = json.loads(raw_path.read_text(encoding='utf-8'))
            if raw.get('batch_id') != doc['batch_id'] or raw.get('schema_version') != '1.0':
                return None
            rows = raw['cases']
            ids = [c['case_run_id'] for c in doc['cases']]
            if [c['case_run_id'] for c in rows] != ids:
                return None
            cases = []
            previous = {c['case_run_id']: c for c in doc['cases']}
            for row in rows:
                cid = row['case_run_id']
                if row['state'] in {'queued', 'not_executed'}:
                    cases.append(CaseResult(case_run_id=cid, state=row['state']).model_dump(mode='json'))
                    continue
                if row['state'] in TERMINAL and previous[cid]['state'] == row['state'] and len(previous[cid]['screenshots']) == 3:
                    cases.append(previous[cid])
                    continue
                target = path / cid
                target.mkdir(exist_ok=True)
                # Only allowlisted IPC fields and fixed PNGs are published.
                try:
                    await asyncio.to_thread(engine.copy, doc['batch_id'], f'cases/{cid}/state.json', target / 'state.json')
                    snap = safe_snapshot(target) or {}
                except EngineError:
                    snap = {}
                screenshots = []
                for artifact in snap.get('screenshots', []):
                    dest = target / (artifact + '.png')
                    if not dest.exists():
                        try:
                            await asyncio.to_thread(engine.copy, doc['batch_id'], f'cases/{cid}/{artifact}.png', dest)
                        except EngineError:
                            continue
                    if not dest.is_symlink() and dest.stat().st_size <= 8_000_000 and dest.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n':
                        screenshots.append(artifact)
                case = CaseResult(case_run_id=cid, state=row['state'], screenshots=screenshots,
                    evidence_complete=len(screenshots) == 3,
                    logs=snap.get('logs', []), diagnostic_code=snap.get('diagnostic_code'),
                    **startup_fields(snap),
                    started_at=row.get('started_at'), finished_at=row.get('finished_at'))
                cases.append(case.model_dump(mode='json'))
            if raw.get('state') not in ACTIVE + TERMINAL:
                return None
            return {'state': raw['state'], 'cases': cases}
        except (EngineError, OSError, ValueError, TypeError, KeyError):
            return None

    async def release(self, slot, batch_id):
        await self.db['visual_batch_dispatch'].update_one({'_id': self.ledger, 'host_id': self.host,
            f'slots.{slot}': batch_id}, {'$set': {f'slots.{slot}': None}})

    async def reconcile_slot(self, slot, batch_id, engine):
        doc = await self.db[self.collection].find_one({'batch_id': batch_id, 'host_id': self.host})
        if not doc:
            raise EngineError('DISPATCH_INTERRUPTED')  # Unknown ownership: hold capacity.
        info = await asyncio.to_thread(engine.inspect, batch_id, doc['image_id'])
        if doc['state'] == 'queued':  # Crash between slot claim and durable launch intent.
            if info is None:
                await self.release(slot, batch_id)
            return
        if info is None:
            if doc.get('start_intent'):
                await self.save(doc, {'diagnostic_code': 'ENGINE_UNAVAILABLE'})
                return  # Ambiguous disappearance never frees capacity automatically.
            await self.finish_interrupted(doc)
            await self.release(slot, batch_id)
            return
        if info['status'] == 'created':
            # Recovery never calls start. Remove this owned identity to fence any
            # delayed old start command; retain volume for inspection.
            info = await asyncio.to_thread(engine.remove_unstarted, batch_id, doc['image_id'])
            if info is None:
                await self.finish_interrupted(doc)
                await self.release(slot, batch_id)
            return
        if info['status'] not in {'running', 'exited', 'stopped'}:
            raise EngineError('ENGINE_UNAVAILABLE')
        if info['status'] == 'running' and (doc['cancel_requested'] or self.stopping or not (
            settings.features.visual_runner_lab and settings.features.visual_runner_batches)):
            await asyncio.to_thread(engine.stop, batch_id)
            info = await asyncio.to_thread(engine.inspect, batch_id, doc['image_id'])
            if not info:
                raise EngineError('ENGINE_UNAVAILABLE')
        snapshot = await self.collect(doc, engine)
        if info['status'] in {'exited', 'stopped'} and info['pid'] == 0:
            if snapshot and snapshot['state'] in TERMINAL:
                if any(c['state'] == 'completed' and not c['evidence_complete'] for c in snapshot['cases']):
                    snapshot['diagnostic_code'] = 'EVIDENCE_UNAVAILABLE'
                await self.save(doc, snapshot)
            else:
                await self.finish_interrupted(doc, snapshot)
            await self.release(slot, batch_id)
        elif snapshot:
            # Terminal IPC does not free a slot before container termination.
            snapshot['state'] = 'stopping' if doc['cancel_requested'] else 'running'
            await self.save(doc, snapshot)

    async def finish_interrupted(self, doc, snapshot=None):
        cases = (snapshot or doc)['cases']
        outcome = 'cancelled' if doc.get('cancel_requested') else 'interrupted'
        cases = [{**c, 'state': 'cancelled' if outcome == 'cancelled' else 'not_executed' if c['state'] == 'queued' else 'interrupted'}
                 if c['state'] not in TERMINAL + ['not_executed'] else c for c in cases]
        code = None if outcome == 'cancelled' else doc.get('diagnostic_code') or 'DISPATCH_INTERRUPTED'
        for case in cases:
            if case['state'] not in {'completed', 'failed'}:
                if doc.get('preparation'):
                    case['preparation'] = PreparationDiagnostics.model_validate(doc['preparation']).model_dump(mode='json')
                if code:
                    case['diagnostic_code'] = case.get('diagnostic_code') or code
        await self.save(doc, {'state': outcome, 'cases': cases, 'diagnostic_code': code})

    async def tick(self):
        if settings.app_env.strip().lower() not in {'development', 'local', 'test'}:
            raise EngineError('BATCH_CONFIGURATION_UNAVAILABLE')
        ledger = await self.db['visual_batch_dispatch'].find_one({'_id': self.ledger, 'host_id': self.host})
        if not ledger:
            raise EngineError('BATCH_CONFIGURATION_UNAVAILABLE')
        engine = self.engine()
        occupied = [(slot, identity) for slot, identity in ledger['slots'].items() if identity]
        if self.collection == 'visual_batch_checks':
            # Independent reconciliation must not serialize five stop/copy cycles.
            results = await asyncio.gather(*(self.reconcile_slot(slot, identity, engine)
                for slot, identity in occupied), return_exceptions=True)
            if any(isinstance(result, BaseException) for result in results):
                raise EngineError('ENGINE_UNAVAILABLE')
        else:
            for slot, batch_id in occupied:
                await self.reconcile_slot(slot, batch_id, engine)
        if self.stopping or not (settings.features.visual_runner_lab and settings.features.visual_runner_batches):
            queued = await self.db[self.collection].find({'host_id': self.host, 'state': 'queued', 'execution_strategy': {'$ne': 'parallel-checks-v1'}}).limit(100).to_list(100)
            for doc in queued:
                await self.db[self.collection].update_one({'_id': doc['_id'], 'state': 'queued'},
                    {'$set': {'state': 'cancelled', 'cancel_requested': True, 'updated_at': now().isoformat(),
                              'cases': [{**c, 'state': 'cancelled'} for c in doc['cases']]}})
            return
        if not self.launch_enabled:
            return
        # Existing Windows lab has its own singleton. Do not overlap modes.
        if await self.db['visual_lab_runs'].find_one({'state': {'$in': OLD_ACTIVE}}):
            return
        ledger = await self.db['visual_batch_dispatch'].find_one({'_id': self.ledger})
        launches = []
        for slot in [str(i) for i in range(self.slot_count)]:
            if slot not in ledger['slots']:
                await self.db['visual_batch_dispatch'].update_one({'_id': self.ledger, f'slots.{slot}': {'$exists': False}}, {'$set': {f'slots.{slot}': None}})
                ledger['slots'][slot] = None
            if sum(bool(v) for v in ledger['slots'].values()) >= self.slot_count:
                break
            if ledger['slots'][slot]:
                continue
            pipeline = [{'$match': {'host_id': self.host, 'state': 'queued', 'cancel_requested': False, 'execution_strategy': {'$ne': 'parallel-checks-v1'}}},
                {'$sort': {'created_at': 1, '_id': 1}},
                {'$group': {'_id': {'account': '$account_id', 'project': '$project_id', 'batch': '$parent_batch_id'}, 'head': {'$first': '$$ROOT'}}},
                {'$replaceRoot': {'newRoot': '$head'}}, {'$sort': {'created_at': 1}}, {'$limit': 100}]
            candidates = await self.db[self.collection].aggregate(pipeline).to_list(100)
            candidates.sort(key=lambda d: (d['account_id'] == ledger.get('last_account'), d['project_id'] == ledger.get('last_project'), d.get('parent_batch_id') == ledger.get('last_batch'), d['created_at']))
            for doc in candidates:
                active = await self.db[self.collection].find({'host_id': self.host, 'state': {'$in': ACTIVE}}).to_list(100)
                if sum(d['account_id'] == doc['account_id'] for d in active) >= settings.visual_batch_account_slots or sum(d['project_id'] == doc['project_id'] for d in active) >= settings.visual_batch_project_slots:
                    continue
                claimed = await self.db['visual_batch_dispatch'].find_one_and_update({'_id': self.ledger,
                    'host_id': self.host, f'slots.{slot}': None}, {'$set': {f'slots.{slot}': doc['batch_id'],
                    'last_account': doc['account_id'], 'last_project': doc['project_id'], 'last_batch': doc.get('parent_batch_id')}}, return_document=ReturnDocument.AFTER)
                if not claimed:
                    break
                intent = await self.db[self.collection].find_one_and_update({'_id': doc['_id'], 'state': 'queued', 'cancel_requested': False},
                    {'$set': {'state': 'starting', 'updated_at': now().isoformat()}}, return_document=ReturnDocument.AFTER)
                if not intent:
                    await self.release(slot, doc['batch_id'])
                    break
                ledger = claimed
                launches.append((doc, intent))
                break
        # Reserve every slot durably before independent container initialization.
        # This is concurrent first-attempt dispatch, never a browser-workflow retry.
        if launches:
            await asyncio.gather(*(self.launch(doc, intent, engine) for doc, intent in launches))

    async def launch(self, doc, intent, engine):
        preparation = PreparationDiagnostics(stage='workspace')
        stage_started = time.monotonic()
        loop = asyncio.get_running_loop()

        async def mark(stage, phase, elapsed=None, reason=None):
            nonlocal stage_started
            preparation.stage = stage
            if phase == 'started':
                stage_started = time.monotonic()
            elif elapsed is not None:
                preparation.timings_ms[stage] = elapsed
            if phase == 'failed' and preparation.error_stage is None:
                preparation.error_stage = stage
                preparation.reason = reason if reason in {'command_timeout', 'process_launch_failed',
                    'command_failed', 'filesystem_error', 'persistence_error', 'invalid_configuration'} else 'unknown'
            preparation.events.append(PreparationEvent(stage=stage, phase=phase, at=now()))
            try:
                await asyncio.wait_for(self.save(intent, {'preparation': preparation.model_dump(mode='json')}), 10)
            except Exception:
                raise EngineError('ENGINE_UNAVAILABLE', reason='persistence_error') from None

        def progress(stage, phase, elapsed, reason):
            # Called only by this trusted engine thread. Persist a stage before its
            # command runs; no secret-bearing arguments/output enter this record.
            future = asyncio.run_coroutine_threadsafe(mark(stage, phase, elapsed, reason), loop)
            try:
                future.result(timeout=11)
            except Exception:
                future.cancel()
                raise EngineError('ENGINE_UNAVAILABLE', reason='persistence_error') from None

        async def complete(stage):
            await mark(stage, 'completed', round((time.monotonic()-stage_started)*1000))

        try:
            await mark('workspace', 'started')
            path = local_path(doc['batch_id'])
            path.mkdir(parents=True, exist_ok=True)
            manifest_path = path / 'manifest.json'
            manifest_path.write_text(json.dumps(doc['manifest']), encoding='utf-8')
            await complete('workspace')
            await asyncio.to_thread(engine.prepare, doc['batch_id'], doc['image_id'], manifest_path, progress=progress)
            if doc.get('parent_batch_id'):
                await mark('parent_authorization', 'started')
                parent = await self.db['visual_batches'].find_one({'batch_id': doc['parent_batch_id'],
                    'host_id': self.host, 'cancel_requested': False, 'state': {'$in': ['queued', *ACTIVE]}})
                await complete('parent_authorization')
                if not parent:
                    await self.db[self.collection].update_one({'_id': doc['_id'], 'state': {'$in': ACTIVE}},
                        {'$set': {'cancel_requested': True, 'state': 'stopping'}})
                    return
            await mark('launch_intent', 'started')
            launch = await self.db[self.collection].update_one({'_id': doc['_id'], 'state': 'starting', 'cancel_requested': False},
                {'$set': {'start_intent': True}})
            await complete('launch_intent')
            if launch.modified_count and not self.stopping and settings.features.visual_runner_batches and settings.features.visual_runner_lab:
                await mark('container_start', 'started')
                await asyncio.to_thread(engine.start, doc['batch_id'])
                await complete('container_start')
        except (EngineError, OSError) as exc:
            if preparation.error_stage is None:
                reason = exc.reason if isinstance(exc, EngineError) else 'filesystem_error'
                await mark(preparation.stage, 'failed', round((time.monotonic()-stage_started)*1000), reason)
            await self.save(intent, {'diagnostic_code': 'ENGINE_UNAVAILABLE', 'preparation': preparation.model_dump(mode='json')})

    async def run(self):
        # The kernel lock serializes all controllers sharing this development host.
        # Mongo slot ownership is durable; no lease-expiry takeover/replay.
        lock = None
        initialized = False
        try:
            while not self.stopping:
                if not initialized and (settings.visual_batch_podman or (
                    settings.features.visual_runner_batches and settings.features.visual_runner_lab)):
                    ROOT.mkdir(parents=True, exist_ok=True)
                    try:
                        lock = open(ROOT / 'dispatcher.lock', 'a+b')
                        if os.name == 'nt':
                            import msvcrt
                            lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
                            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        await self.initialize()
                        initialized = True
                    except Exception:
                        self.last_error = 'ENGINE_UNAVAILABLE'
                        if lock:
                            lock.close()
                        lock = None
                if initialized:
                    try:
                        await self.tick()
                        self.last_error = None
                    except Exception:
                        self.last_error = 'ENGINE_UNAVAILABLE'  # No raw paths/output/secrets.
                await asyncio.sleep(1)
        finally:
            if initialized:
                try:
                    await self.tick()  # Request bounded termination; do not release unknown slots.
                except Exception:
                    pass
            if lock:
                lock.close()

    async def shutdown(self):
        self.stopping = True
        if self.task:
            try:
                await asyncio.wait_for(asyncio.shield(self.task), 40)
            except asyncio.TimeoutError:
                pass  # Container's own bounded watchdog remains; restart reconciliation never replays.



CHECK_LEDGER = 'local-linux-check-pool-v1'


def aggregate_cases(cases, cancelled=False):
    states = [c['state'] for c in cases]
    if any(s in ACTIVE for s in states):
        return 'stopping' if cancelled else 'running'
    if 'queued' in states:
        return 'stopping' if cancelled else 'queued'
    if cancelled or 'cancelled' in states:
        return 'cancelled'
    for outcome in ['interrupted', 'timed_out', 'failed', 'not_executed']:
        if outcome in states:
            return 'interrupted' if outcome == 'not_executed' else outcome
    return 'completed'


class ParallelVisualBatchService(VisualBatchService):
    """Batch grouping facade; each durable child owns one container and slot.

    Reuses the immutable v1 runner protocol with exactly one case. Old batch
    manifests/containers are drained through the old controller before this pool
    launches anything. Only one host/checkout controller may call tick (kernel lock).
    """
    def __init__(self, database=None, engine=None, host=None):
        super().__init__(database, engine, host, strategy='parallel-checks-v1')
        self.checks = VisualBatchService(self.db, engine, self.host,
            collection='visual_batch_checks', ledger=CHECK_LEDGER, slots=settings.visual_batch_global_slots)

    async def initialize(self):
        await super().initialize()
        await self.checks.initialize()
        await self.db['visual_batch_checks'].create_index([('parent_batch_id', 1)])

    async def materialize(self, parent):
        # Deterministic child _id makes crash-partial materialization idempotent.
        # No transaction/resume is needed: insert missing queue records only;
        # existing starting/terminal jobs are never reset or started again.
        for fixture in parent['manifest']['cases']:
            cid = fixture['case_run_id']
            manifest = BatchManifest(batch_id=cid, cases=[FixtureCase(**fixture)], batch_timeout_seconds=110)
            run = CheckDispatch(parent_batch_id=parent['batch_id'], batch_id=cid, project_id=parent['project_id'], state='queued', manifest=manifest,
                cases=[CaseResult(case_run_id=cid)], created_at=parent['created_at'], updated_at=parent['updated_at'])
            child = {**run.model_dump(mode='json'), '_id': cid, 'parent_batch_id': parent['batch_id'],
                'account_id': parent['account_id'], 'host_id': self.host, 'image_id': parent['image_id'],
                'created_by': parent['created_by'], 'cancel_requested': False, 'start_intent': False}
            await self.db['visual_batch_checks'].update_one({'_id': cid}, {'$setOnInsert': child}, upsert=True)

    async def sync_parent(self, parent):
        children = await self.db['visual_batch_checks'].find({'parent_batch_id': parent['batch_id']}).to_list(10)
        if len(children) != len(parent['cases']):
            return
        by_id = {d['batch_id']: d for d in children}
        cases = []
        for old in parent['cases']:
            child = by_id[old['case_run_id']]
            case = {**child['cases'][0], 'state': child['state']}
            case['diagnostic_code'] = case.get('diagnostic_code') or child.get('diagnostic_code')
            if child.get('preparation'):
                case['preparation'] = PreparationDiagnostics.model_validate(child['preparation']).model_dump(mode='json')
            # Publish only fixed sanitized IPC/PNG files to the existing authorized
            # artifact layout. No profiles, symlinks or raw engine logs are copied.
            source = local_path(child['batch_id']) / child['batch_id']
            target = local_path(parent['batch_id']) / child['batch_id']
            if source.is_dir() and not source.is_symlink():
                target.mkdir(parents=True, exist_ok=True)
                if target.is_symlink():
                    raise EngineError('EVIDENCE_UNAVAILABLE')
                for name in ['state.json', *[a + '.png' for a in case['screenshots']]]:
                    src, dest = source / name, target / name
                    if src.is_file() and not src.is_symlink() and not dest.is_symlink() and src.stat().st_size <= 8_000_000:
                        shutil.copyfile(src, dest)
            published = []
            for artifact in case['screenshots']:
                png = target / (artifact + '.png')
                if png.is_file() and not png.is_symlink() and png.stat().st_size <= 8_000_000 and png.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n':
                    published.append(artifact)
            case['screenshots'] = published
            case['evidence_complete'] = len(published) == 3
            cases.append(case)
        state = aggregate_cases(cases, parent['cancel_requested'])
        # Cancellation raced with collection? Do not overwrite it; next tick
        # propagates cancellation and collects independently completed evidence.
        await self.db['visual_batches'].update_one({'_id': parent['_id'],
            'state': {'$in': ['queued', *ACTIVE]}, 'cancel_requested': parent['cancel_requested']},
            {'$set': {'cases': cases, 'state': state, 'updated_at': now().isoformat()}})

    async def tick(self):
        # Never let legacy queued work launch alongside occupied check slots.
        pool = await self.db['visual_batch_dispatch'].find_one({'_id': CHECK_LEDGER})
        self.launch_enabled = not pool or not any(pool['slots'].values())
        # Drain existing sequential batches, including their durable occupied slots.
        await super().tick()
        if settings.app_env.strip().lower() not in {'development', 'local', 'test'}:
            return
        parents = await self.db['visual_batches'].find({'host_id': self.host,
            'execution_strategy': 'parallel-checks-v1', 'state': {'$in': ['queued', *ACTIVE]}}).limit(100).to_list(100)
        disabled = self.stopping or not (settings.features.visual_runner_lab and settings.features.visual_runner_batches)
        for parent in parents:
            if disabled and not parent['cancel_requested']:
                await self.db['visual_batches'].update_one({'_id': parent['_id'], 'state': {'$in': ['queued', *ACTIVE]}},
                    {'$set': {'cancel_requested': True, 'state': 'stopping'}})
                parent['cancel_requested'] = True
            await self.materialize(parent)
            if parent['cancel_requested']:
                for fixture in parent['manifest']['cases']:
                    await self.cancel_child(fixture['case_run_id'])
        # Ledger ownership is stronger than parent lifecycle. Never overlap old
        # two-slot containers with the new pool, including ambiguous old slots.
        legacy = await self.db['visual_batch_dispatch'].find_one({'_id': self.ledger})
        self.checks.stopping = disabled
        if not any(legacy['slots'].values()):
            await self.checks.tick()
        for parent in parents:
            fresh = await self.db['visual_batches'].find_one({'_id': parent['_id']})
            await self.sync_parent(fresh)

    async def cancel(self, project_id, batch_id):
        run = await self.get(project_id, batch_id)
        if run.execution_strategy != 'parallel-checks-v1':
            return await super().cancel(project_id, batch_id)
        await self.db['visual_batches'].update_one({'batch_id': batch_id, 'project_id': project_id,
            'state': {'$in': ['queued', *ACTIVE]}}, {'$set': {'cancel_requested': True,
                'state': 'stopping', 'updated_at': now().isoformat()}})
        return await self.get(project_id, batch_id)

    async def cancel_child(self, cid):
        # Feature-off reconciliation cannot call API guards.
        doc = await self.db['visual_batch_checks'].find_one_and_update({'_id': cid, 'host_id': self.host,
            'state': 'queued'}, {'$set': {'state': 'cancelled', 'cancel_requested': True}},
            return_document=ReturnDocument.AFTER)
        if doc:
            await self.db['visual_batch_checks'].update_one({'_id': cid, 'state': 'cancelled'},
                {'$set': {'cases': [{**c, 'state': 'cancelled'} for c in doc['cases']]}})
        else:
            await self.db['visual_batch_checks'].update_one({'_id': cid, 'host_id': self.host,
                'state': {'$in': ACTIVE}}, {'$set': {'cancel_requested': True, 'state': 'stopping'}})


visual_batches = ParallelVisualBatchService()
