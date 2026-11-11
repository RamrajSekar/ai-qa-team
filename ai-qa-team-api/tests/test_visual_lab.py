"""Isolated authorization/service checks: no live database, browser, Redis or AI."""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import time
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {'MONGO_URI': 'mongodb://localhost:27017', 'MONGO_DB': 'lab_tests',
            'REDIS_HOST': 'localhost', 'REDIS_PORT': '6379', 'REDIS_USERNAME': 'test',
            'REDIS_PASSWORD': 'test', 'SESSION_SECRET_KEY': 'test', 'JWT_SECRET_KEY': 'test'}
with patch.dict(os.environ, TEST_ENV):
    from app.config import FeatureFlags, settings
    from app.models.visual_lab_model import VisualLabRun
    from app.routes import visual_lab_routes as routes
    from app.services import visual_lab_service as service
    from app.utils.auth_dependency import get_current_user

from fastapi import FastAPI, HTTPException
import httpx
from pymongo.errors import DuplicateKeyError


class LabTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.old_flags = settings.features
        self.old_env = settings.app_env
        settings.features = FeatureFlags(visual_runner_lab=True)
        settings.app_env = 'test'
        self.app = FastAPI()
        self.app.include_router(routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {'email': 'member@example.test'}
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://test')
        self.member = patch.object(routes, 'require_project_member', new_callable=AsyncMock)
        self.auth = self.member.start()

    async def asyncTearDown(self):
        await self.client.aclose()
        self.member.stop()
        settings.features = self.old_flags
        settings.app_env = self.old_env

    def run_doc(self):
        return VisualLabRun(run_id='a'*32, project_id='p1', state='running', headed=False,
                            created_at='2026-10-31T00:00:00+00:00', updated_at='2026-10-31T00:00:00+00:00')

    async def test_disabled_all_operations_before_auth_or_service(self):
        settings.features.visual_runner_lab = False
        for method, suffix in [('POST', '/runs'), ('GET', '/runs'), ('GET', '/runs/'+'a'*32),
                               ('POST', '/runs/'+'a'*32+'/cancel'), ('GET', '/runs/'+'a'*32+'/artifacts/01-open')]:
            response = await self.client.request(method, '/projects/p1/visual-lab'+suffix, json={})
            self.assertEqual(response.status_code, 403)
        self.auth.assert_not_awaited()

    async def test_membership_required_for_start_status_cancel_artifacts(self):
        self.auth.side_effect = HTTPException(404, 'Project not found or access denied')
        for method, suffix in [('POST', '/runs'), ('GET', '/runs'), ('GET', '/runs/'+'a'*32),
                               ('POST', '/runs/'+'a'*32+'/cancel'), ('GET', '/runs/'+'a'*32+'/artifacts/01-open')]:
            response = await self.client.request(method, '/projects/other/visual-lab'+suffix, json={})
            self.assertEqual(response.status_code, 404)

    async def test_authorized_start_status_cancel_and_no_arbitrary_inputs(self):
        with patch.object(service.visual_lab, 'start', new_callable=AsyncMock, return_value=self.run_doc()) as start, \
             patch.object(service.visual_lab, 'reconcile', new_callable=AsyncMock, return_value=self.run_doc()) as status, \
             patch.object(service.visual_lab, 'cancel', new_callable=AsyncMock, return_value=self.run_doc()) as cancel:
            self.assertEqual((await self.client.post('/projects/p1/visual-lab/runs', json={'headed': True})).status_code, 202)
            start.assert_awaited_once_with('p1', {'email': 'member@example.test'}, True)
            self.assertEqual((await self.client.get('/projects/p1/visual-lab/runs/'+'a'*32)).status_code, 200)
            self.assertEqual((await self.client.post('/projects/p1/visual-lab/runs/'+'a'*32+'/cancel')).status_code, 200)
            self.assertEqual((await self.client.post('/projects/p1/visual-lab/runs', json={'url': 'http://evil'})).status_code, 422)

    async def test_cross_project_run_lookup_scoped_and_artifacts_allowlisted(self):
        database = MagicMock()
        database.__getitem__.return_value.find_one = AsyncMock(return_value=None)
        with patch.object(service, 'db', database):
            response = await self.client.get('/projects/p2/visual-lab/runs/'+'a'*32)
            self.assertEqual(response.status_code, 404)
            database.__getitem__.return_value.find_one.assert_awaited_with({'run_id': 'a'*32, 'project_id': 'p2'})
        with patch.object(service.visual_lab, 'reconcile', new_callable=AsyncMock, return_value=self.run_doc()):
            self.assertEqual((await self.client.get('/projects/p1/visual-lab/runs/'+'a'*32+'/artifacts/config.json')).status_code, 404)

    async def test_screenshot_authorized_and_no_paths(self):
        run = self.run_doc()
        run.screenshots = ['01-open']
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2] / 'tmp') as folder:
            path = Path(folder)
            (path / '01-open.png').write_bytes(b'fixture-png')
            with patch.object(routes, 'workspace', return_value=path), \
                 patch.object(service.visual_lab, 'reconcile', new_callable=AsyncMock, return_value=run):
                response = await self.client.get('/projects/p1/visual-lab/runs/'+'a'*32+'/artifacts/01-open')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b'fixture-png')
                self.assertEqual(response.headers['cache-control'], 'no-store')

    async def test_duplicate_atomic_lease_prevents_launch(self):
        database = MagicMock()
        database.__getitem__.return_value.find_one = AsyncMock(return_value=None)
        database.__getitem__.return_value.find_one_and_update = AsyncMock(side_effect=DuplicateKeyError('busy'))
        with patch.object(service, 'db', database), patch.object(service.Path, 'is_file', return_value=True), \
             patch.object(settings, 'visual_runner_chrome', 'fixture-chrome'), \
             patch.object(settings, 'visual_runner_driver', 'fixture-driver'), patch.object(service.subprocess, 'Popen') as launch:
            with self.assertRaises(HTTPException) as caught:
                await service.visual_lab.start('p1', {'email': 'tester'}, False)
            self.assertEqual(caught.exception.status_code, 409)
            launch.assert_not_called()

    async def test_feature_off_cannot_overlap_occupied_linux_capacity(self):
        database = MagicMock()
        database.__getitem__.return_value.find_one = AsyncMock(return_value={'slots':{'0':'owned-check'}})
        with patch.object(service, 'db', database), patch.object(service.subprocess, 'Popen') as launch:
            with self.assertRaises(HTTPException) as caught:
                await service.visual_lab.start('p1', {'email':'tester'}, False)
            self.assertEqual(caught.exception.status_code, 409)
            launch.assert_not_called()

    async def test_production_rejected_even_when_flag_enabled(self):
        settings.app_env = 'production'
        self.assertEqual((await self.client.post('/projects/p1/visual-lab/runs', json={})).status_code, 403)

    async def test_runner_inherits_windows_context_but_not_application_secrets(self):
        manager = service.VisualLabService()
        database = MagicMock()
        collection = database.__getitem__.return_value
        collection.find_one = AsyncMock(return_value=None)
        collection.find_one_and_update = AsyncMock(return_value={'run_id': 'fixture'})
        collection.insert_one = AsyncMock()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2] / 'tmp') as folder:
            with patch.object(service, 'db', database), patch.object(service.Path, 'is_file', return_value=True), \
                 patch.object(service, 'workspace', return_value=Path(folder)/'run'), \
                 patch.object(settings, 'visual_runner_chrome', 'fixture-chrome'), \
                 patch.object(settings, 'visual_runner_driver', 'fixture-driver'), \
                 patch.object(manager, 'monitor', new_callable=AsyncMock), \
                 patch.object(service.subprocess, 'Popen') as launch, \
                 patch.dict(os.environ, {'SYSTEMDRIVE':'C:', 'PROGRAMDATA':'C:/ProgramData', 'OPENAI_API_KEY':'secret-canary'}):
                await manager.start('p1', {'email':'synthetic@example.test'}, False)
                env = launch.call_args.kwargs['env']
                self.assertEqual(env['SYSTEMDRIVE'], 'C:')
                self.assertEqual(env['PROGRAMDATA'], 'C:/ProgramData')
                self.assertNotIn('OPENAI_API_KEY', env)
                self.assertNotIn('MONGO_URI', env)
                self.assertNotIn('JWT_SECRET_KEY', env)
                await asyncio.gather(*list(manager.tasks))

    async def test_interrupted_supervisor_reconciles_and_filters_diagnostics(self):
        manager = service.VisualLabService()
        doc = {**self.run_doc().model_dump(), 'host_id': manager.lock_id}
        database = MagicMock()
        collection = database.__getitem__.return_value
        collection.find_one = AsyncMock(return_value=doc)
        collection.update_one = AsyncMock()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[2] / 'tmp') as folder:
            path = Path(folder)
            (path / 'heartbeat').touch()
            os.utime(path / 'heartbeat', (time.time()-30, time.time()-30))
            with patch.object(service, 'db', database), patch.object(service, 'workspace', return_value=path):
                restored = await manager.reconcile('a'*32, 'p1')
                self.assertEqual(restored.state, 'interrupted')
                self.assertEqual(restored.logs, ['Backend supervision stopped.'])
            (path / 'state.json').write_text(json.dumps({'state': 'completed', 'logs': ['private-value', 'Browser smoke check completed'],
                'screenshots': ['../../config', '01-open'], 'browser_version': 'private-value', 'diagnostic_code': 'private-value',
                'startup_stage': 'private-value', 'startup_reason': 'private-value',
                'startup_timings_ms': {'private-value': 5, 'driver_launch': 10, 'session_creation': -1, 'ready': True}}))
            snapshot = service.safe_snapshot(path)
            self.assertEqual(snapshot['logs'], ['Browser smoke check completed'])
            self.assertEqual(snapshot['screenshots'], ['01-open'])
            self.assertIsNone(snapshot['browser_version'])
            self.assertIsNone(snapshot['diagnostic_code'])
            self.assertIsNone(snapshot['startup_stage'])
            self.assertIsNone(snapshot['startup_reason'])
            self.assertEqual(snapshot['startup_timings_ms'], {'driver_launch': 10})

    async def test_startup_bundle_filters_untrusted_fields_and_types(self):
        raw = {'driver_version': '146.0.7680.31', 'driver_state': 'running',
               'driver_exit_code': True, 'cleanup_driver_exit_code': -1,
               'browser_state': 'private-value', 'devtools_port_file': ['private-value'],
               'session_created': 'true', 'cleanup': 'unverified', 'path': 'secret-canary',
               'native_errors': ['access_denied', 'secret-canary', {}, 'access_denied']}
        safe = service.safe_startup_diagnostics(raw)
        self.assertEqual(safe, {'driver_version': '146.0.7680.31', 'driver_state': 'running',
            'cleanup_driver_exit_code': -1, 'cleanup': 'unverified', 'native_errors': ['access_denied']})
        self.assertNotIn('secret-canary', json.dumps(safe))
        self.assertEqual(service.safe_startup_diagnostics({'driver_version': 'secret-canary',
            'driver_exit_code': 2**64, 'native_errors': 'private-value'}), {})
        self.assertIsNone(service.safe_startup_diagnostics(None))


if __name__ == '__main__':
    unittest.main()
