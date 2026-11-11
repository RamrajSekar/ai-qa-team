"""Contract/authorization checks; Mongo/engine/auth doubles explicitly isolated."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {'MONGO_URI': 'mongodb://localhost:27017', 'MONGO_DB': 'batch_unit_tests',
    'REDIS_HOST': 'localhost', 'REDIS_PORT': '6399', 'REDIS_USERNAME': '', 'REDIS_PASSWORD': '',
    'SESSION_SECRET_KEY': 'test', 'JWT_SECRET_KEY': 'test'}):
    from app.config import FeatureFlags, settings
    from app.models.visual_batch_model import BatchManifest, BatchStart, FixtureCase, BatchRun, CaseResult
    from app.routes import visual_batch_routes as routes
    from app.services.visual_batch_service import VisualBatchService
    from app.services.visual_batch_engine import EngineError
    from app.utils.auth_dependency import get_current_user

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError


class ContractTests(unittest.TestCase):
    def test_legacy_case_diagnostics_enriched_read_only_and_sanitized(self):
        from app.services import visual_batch_service as service
        from datetime import datetime, timezone
        manifest = BatchManifest(batch_id='a'*32, cases=[FixtureCase(case_run_id='b'*32)], batch_timeout_seconds=110)
        doc = BatchRun(batch_id='a'*32, project_id='p', state='failed', manifest=manifest,
            cases=[CaseResult(case_run_id='b'*32, state='failed')], created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)).model_dump(mode='json')
        original = json.dumps(doc)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2] / 'tmp') as folder:
            path = Path(folder) / ('a'*32) / ('b'*32)
            path.mkdir(parents=True)
            (path/'state.json').write_text(json.dumps({'state':'failed', 'startup_stage':'session_handshake',
                'startup_timings_ms':{'browser_launch':37667, 'private-canary':9},
                'startup_diagnostics':{'session_created':False,'driver_state':'running','path':'private-canary',
                    'native_errors':['private-canary','access_denied']}}))
            saved = (path/'state.json').read_bytes()
            with patch.object(service, 'ROOT', Path(folder)), patch.object(service, 'PodmanBatchEngine') as engine:
                result = service.public(doc)
                engine.assert_not_called()
            self.assertEqual(result.cases[0].startup_stage, 'session_handshake')
            self.assertEqual(result.cases[0].startup_timings_ms, {'browser_launch':37667})
            self.assertFalse(result.cases[0].startup_diagnostics.session_created)
            self.assertNotIn('private-canary', result.model_dump_json())
            self.assertEqual((path/'state.json').read_bytes(), saved)
        self.assertEqual(json.dumps(doc), original)

    def test_bounds_and_arbitrary_input_rejected(self):
        for count in [0, 11, True, '2']:
            with self.subTest(count=count), self.assertRaises(ValidationError):
                BatchStart(idempotency_key='a'*32, case_count=count)
        for extra in [{'url': 'https://invalid.test'}, {'keyword': 'Run'}, {'headed': True}, {'image': 'anything'}]:
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                BatchStart(idempotency_key='a'*32, case_count=1, **extra)
        for count in [1, 10]:
            self.assertEqual(BatchStart(idempotency_key='a'*32, case_count=count).case_count, count)

    def test_manifest_version_identity_and_budget(self):
        partial = CaseResult(case_run_id='b'*32, startup_diagnostics={})
        self.assertIsNone(partial.startup_diagnostics.session_created)
        self.assertEqual(partial.startup_diagnostics.cleanup, 'unverified')
        case = FixtureCase(case_run_id='b'*32)
        with self.assertRaises(ValidationError):
            BatchManifest(batch_id='a'*32, cases=[case, case], batch_timeout_seconds=220)
        with self.assertRaises(ValidationError):
            BatchManifest(batch_id='a'*32, cases=[case], batch_timeout_seconds=111)
        with self.assertRaises(ValidationError):
            BatchManifest(schema_version='2.0', batch_id='a'*32, cases=[case], batch_timeout_seconds=110)

    def test_exported_schema_and_runner_agree(self):
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / 'visual-runner'))
        sys.path.insert(0, str(root / 'ai-qa-team-api/scripts'))
        from linux.contract_validation import validate_manifest
        from export_visual_batch_contract import exported_schema, exported_typescript
        schema = root / 'visual-runner/linux/batch-manifest.schema.json'
        self.assertEqual(schema.read_text(encoding='utf-8'), exported_schema())
        self.assertEqual((root / 'ai-qa-team-ui/src/types/visual-batch.generated.ts').read_text(encoding='utf-8'), exported_typescript())
        manifest = BatchManifest(batch_id='a'*32, cases=[FixtureCase(case_run_id='b'*32)], batch_timeout_seconds=110).model_dump(mode='json')
        validate_manifest(manifest)
        for field, value in [('schema_version', '2.0'), ('url', 'https://invalid.test'), ('case_timeout_seconds', True)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_manifest({**manifest, field: value})


class AuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.flags, self.env = settings.features, settings.app_env
        settings.features = FeatureFlags(visual_runner_lab=True, visual_runner_batches=True)
        settings.app_env = 'test'
        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[get_current_user] = lambda: {'email': 'member@example.test'}
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')
        self.auth = patch.object(routes, 'require_project_member', new_callable=AsyncMock)
        self.member = self.auth.start()
        self.member.return_value = ({'created_by': 'owner@example.test'}, {})
        self.paths = [('POST', ''), ('GET', ''), ('GET', '/'+'a'*32), ('POST', '/'+'a'*32+'/cancel'),
                      ('GET', '/'+'a'*32+'/cases/'+'b'*32+'/artifacts/01-open')]

    async def asyncTearDown(self):
        await self.client.aclose()
        self.auth.stop()
        settings.features, settings.app_env = self.flags, self.env

    async def test_both_flags_and_development_required_for_every_operation(self):
        for flag in ['visual_runner_lab', 'visual_runner_batches']:
            setattr(settings.features, flag, False)
            for method, suffix in self.paths:
                response = await self.client.request(method, '/projects/p/visual-lab/batches'+suffix, json={})
                self.assertEqual(response.status_code, 403)
            setattr(settings.features, flag, True)
        settings.app_env = 'production'
        self.assertEqual((await self.client.get('/projects/p/visual-lab/batches')).status_code, 403)
        self.member.assert_not_awaited()

    async def test_cross_project_denied_for_every_operation(self):
        self.member.side_effect = HTTPException(404, 'No project access')
        for method, suffix in self.paths:
            response = await self.client.request(method, '/projects/other/visual-lab/batches'+suffix, json={})
            self.assertEqual(response.status_code, 404)

    async def test_no_command_or_url_inputs(self):
        with patch.object(routes.visual_batches, 'enqueue', new_callable=AsyncMock) as enqueue:
            response = await self.client.post('/projects/p/visual-lab/batches', json={
                'idempotency_key': 'a'*32, 'case_count': 1, 'url': 'http://invalid.test'})
            self.assertEqual(response.status_code, 422)
            enqueue.assert_not_awaited()

    async def test_missing_cross_project_batch_has_scoped_lookup(self):
        database = unittest.mock.MagicMock()
        database.__getitem__.return_value.find_one = AsyncMock(return_value=None)
        manager = VisualBatchService(database=database)
        with self.assertRaises(HTTPException) as exc:
            await manager.get('other', 'a'*32)
        self.assertEqual(exc.exception.status_code, 404)
        database.__getitem__.return_value.find_one.assert_awaited_once_with({'batch_id': 'a'*32, 'project_id': 'other'})

    async def test_engine_unknown_does_not_release_capacity(self):
        database = unittest.mock.MagicMock()
        doc = {'batch_id': 'a'*32, '_id': 'key', 'state': 'running', 'start_intent': True, 'image_id': 'c'*64}
        database.__getitem__.return_value.find_one = AsyncMock(return_value=doc)
        manager = VisualBatchService(database=database)
        manager.release = AsyncMock()
        engine = unittest.mock.MagicMock()
        engine.inspect.side_effect = EngineError('ENGINE_UNAVAILABLE')
        with self.assertRaises(EngineError):
            await manager.reconcile_slot('0', doc['batch_id'], engine)
        manager.release.assert_not_awaited()

    async def test_disabled_restart_still_initializes_reconciliation_when_engine_configured(self):
        settings.features.visual_runner_batches = False
        manager = VisualBatchService()
        manager.initialize = AsyncMock()
        async def tick():
            manager.stopping = True
        manager.tick = AsyncMock(side_effect=tick)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2] / 'tmp') as folder:
            with patch.object(settings, 'visual_batch_podman', 'configured-local-engine'), patch('app.services.visual_batch_service.ROOT', Path(folder)):
                await manager.run()
        manager.initialize.assert_awaited_once()
        self.assertGreaterEqual(manager.tick.await_count, 1)

    async def test_production_tick_stops_before_database_and_engine(self):
        settings.app_env = 'production'
        manager = VisualBatchService(database=unittest.mock.MagicMock())
        with self.assertRaises(EngineError):
            await manager.tick()
        manager.db.__getitem__.assert_not_called()


class ParallelDispatchTests(unittest.TestCase):
    def test_parent_contract_preserves_legacy_defaults(self):
        from app.services.visual_batch_service import ParallelVisualBatchService
        self.assertEqual(VisualBatchService().strategy, 'sequential-batch-v1')
        manager = ParallelVisualBatchService()
        self.assertEqual(manager.strategy, 'parallel-checks-v1')
        self.assertEqual(manager.checks.collection, 'visual_batch_checks')
        self.assertEqual(manager.checks.slot_count, settings.visual_batch_global_slots)
        self.assertNotEqual(manager.ledger, manager.checks.ledger)

    def test_check_dispatch_rejects_mismatched_container_identity(self):
        from app.models.visual_batch_model import CheckDispatch
        from datetime import datetime, timezone
        manifest = BatchManifest(batch_id='a'*32, cases=[FixtureCase(case_run_id='b'*32)], batch_timeout_seconds=110)
        with self.assertRaises(ValidationError):
            CheckDispatch(parent_batch_id='c'*32, batch_id='a'*32, project_id='p', state='queued', manifest=manifest,
                cases=[CaseResult(case_run_id='b'*32)], created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))

    def test_engine_timeout_is_sanitized_and_distinct(self):
        from app.services.visual_batch_engine import PodmanBatchEngine
        import subprocess
        with patch('app.services.visual_batch_engine.Path.is_file', return_value=True):
            engine = PodmanBatchEngine('fixture-podman')
        with patch('app.services.visual_batch_engine.subprocess.run', side_effect=subprocess.TimeoutExpired('private-canary',30)):
            with self.assertRaises(EngineError) as caught:
                engine.command('inspect','fixture')
        self.assertEqual(str(caught.exception), 'ENGINE_UNAVAILABLE')
        self.assertEqual(caught.exception.reason, 'command_timeout')
        self.assertNotIn('private-canary', str(caught.exception))

    def test_aggregate_independent_outcomes_and_cancellation(self):
        from app.services.visual_batch_service import aggregate_cases
        for states, cancel, expected in [
            (['completed']*5, False, 'completed'),
            (['completed', 'running', 'queued'], False, 'running'),
            (['completed', 'running'], True, 'stopping'),
            (['completed', 'cancelled'], True, 'cancelled'),
            (['completed', 'failed'], False, 'failed'),
            (['interrupted', 'queued'], False, 'queued'),
            (['interrupted', 'completed'], False, 'interrupted')]:
            with self.subTest(states=states):
                self.assertEqual(aggregate_cases([{'state': state} for state in states], cancel), expected)


class ParallelMaterializationTests(unittest.IsolatedAsyncioTestCase):
    async def test_occupied_check_pool_prevents_legacy_launch_and_overlap(self):
        from app.services.visual_batch_service import ParallelVisualBatchService
        database = unittest.mock.MagicMock()
        database.__getitem__.return_value.find_one = AsyncMock(side_effect=[
            {'slots': {'0':'check-owner'}}, {'slots': {'0':'legacy-owner'}}])
        database.__getitem__.return_value.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        manager = ParallelVisualBatchService(database=database)
        manager.checks.tick = AsyncMock()
        with patch.object(VisualBatchService, 'tick', new_callable=AsyncMock), patch.object(settings, 'app_env', 'test'):
            await manager.tick()
        self.assertFalse(manager.launch_enabled)
        manager.checks.tick.assert_not_awaited()

    async def test_feature_off_queued_child_cancellation_has_no_api_guard(self):
        from app.services.visual_batch_service import ParallelVisualBatchService
        database = unittest.mock.MagicMock()
        collection = database.__getitem__.return_value
        collection.find_one_and_update = AsyncMock(return_value={'cases':[{'case_run_id':'a'*32, 'state':'queued'}]})
        collection.update_one = AsyncMock()
        manager = ParallelVisualBatchService(database=database)
        with patch.object(settings, 'features', FeatureFlags()):
            await manager.cancel_child('a'*32)
        self.assertEqual(collection.find_one_and_update.await_args.args[1]['$set']['state'], 'cancelled')
        self.assertEqual(collection.update_one.await_args.args[1]['$set']['cases'][0]['state'], 'cancelled')

    async def test_unstarted_cancel_preserves_completed_evidence(self):
        manager = VisualBatchService()
        manager.save = AsyncMock()
        doc = {'cancel_requested':True, 'cases':[{'state':'queued'}, {'state':'completed','screenshots':['01-open']}]}
        await manager.finish_interrupted(doc)
        saved = manager.save.await_args.args[1]
        self.assertEqual(saved['state'], 'cancelled')
        self.assertEqual(saved['cases'][0]['state'], 'cancelled')
        self.assertEqual(saved['cases'][1], doc['cases'][1])

    async def test_cancelled_parent_never_starts_prepared_check(self):
        database = unittest.mock.MagicMock()
        collection = database.__getitem__.return_value
        collection.find_one = AsyncMock(return_value=None)
        collection.update_one = AsyncMock()
        engine = unittest.mock.MagicMock()
        manager = VisualBatchService(database=database, collection='visual_batch_checks')
        doc = {'_id':'a'*32, 'batch_id':'a'*32, 'parent_batch_id':'b'*32, 'image_id':'c'*64, 'manifest':{}}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2] / 'tmp') as folder:
            with patch('app.services.visual_batch_service.ROOT', Path(folder)):
                await manager.launch(doc, doc, engine)
        engine.prepare.assert_called_once()
        engine.start.assert_not_called()
        self.assertTrue(collection.update_one.await_args.args[1]['$set']['cancel_requested'])

    async def test_parent_evidence_does_not_claim_missing_pngs(self):
        from app.services import visual_batch_service as service
        database = unittest.mock.MagicMock()
        collection = database.__getitem__.return_value
        cid, bid = 'a'*32, 'b'*32
        child = {'batch_id':cid, 'state':'completed', 'cases':[{'case_run_id':cid, 'state':'completed',
            'screenshots':['01-open','02-filled','03-confirmed'], 'evidence_complete':True}]}
        collection.find.return_value.to_list = AsyncMock(return_value=[child])
        collection.update_one = AsyncMock()
        manager = service.ParallelVisualBatchService(database=database)
        parent = {'_id':'parent', 'batch_id':bid, 'cancel_requested':False, 'cases':[{'case_run_id':cid}]}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2] / 'tmp') as folder:
            source = Path(folder) / cid / cid
            source.mkdir(parents=True)
            (source/'01-open.png').write_bytes(bytes.fromhex('89504e470d0a1a0a'))
            with patch.object(service, 'ROOT', Path(folder)):
                await manager.sync_parent(parent)
        saved = collection.update_one.await_args.args[1]['$set']['cases'][0]
        self.assertEqual(saved['screenshots'], ['01-open'])
        self.assertFalse(saved['evidence_complete'])

    async def test_one_case_per_deterministic_container_job(self):
        from app.services.visual_batch_service import ParallelVisualBatchService
        from datetime import datetime, timezone
        database = unittest.mock.MagicMock()
        collection = database.__getitem__.return_value
        collection.update_one = AsyncMock()
        manager = ParallelVisualBatchService(database=database)
        timestamp = datetime.now(timezone.utc).isoformat()
        cases = [FixtureCase(case_run_id=f'{i:032x}') for i in range(1, 6)]
        parent = {'batch_id':'a'*32, 'project_id':'p', 'manifest':BatchManifest(batch_id='a'*32,
            cases=cases, batch_timeout_seconds=550).model_dump(mode='json'), 'created_at':timestamp,
            'updated_at':timestamp, 'account_id':'owner', 'image_id':'c'*64, 'created_by':'member'}
        await manager.materialize(parent)
        self.assertEqual(collection.update_one.await_count, 5)
        for call in collection.update_one.await_args_list:
            child = call.args[1]['$setOnInsert']
            self.assertEqual(child['_id'], child['batch_id'])
            self.assertEqual(child['parent_batch_id'], parent['batch_id'])
            self.assertEqual(len(child['manifest']['cases']), 1)
            self.assertEqual(child['manifest']['cases'][0]['case_run_id'], child['batch_id'])
            self.assertEqual(child['manifest']['batch_timeout_seconds'], 110)
            self.assertFalse(child['start_intent'])
            self.assertTrue(call.kwargs['upsert'])


if __name__ == '__main__':
    unittest.main()
