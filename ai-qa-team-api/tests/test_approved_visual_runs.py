"""ASGI admission checks with isolated database and authentication doubles."""
import asyncio
from copy import deepcopy
import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException
from pymongo.errors import DuplicateKeyError

with patch.dict(os.environ, {
    'MONGO_URI': 'mongodb://localhost:27017', 'MONGO_DB': 'approved_visual_tests',
    'REDIS_HOST': 'localhost', 'REDIS_PORT': '6399', 'REDIS_USERNAME': '',
    'REDIS_PASSWORD': '', 'SESSION_SECRET_KEY': 'test', 'JWT_SECRET_KEY': 'test',
}):
    from app.config import FeatureFlags, settings
    from app.routes import approved_visual_runs as routes


class CollectionDouble:
    def __init__(self, *docs):
        self.docs = list(docs)

    @staticmethod
    def matches(doc, query):
        for key, value in query.items():
            current = doc
            for part in key.split('.'):
                current = current.get(part) if isinstance(current, dict) else None
            if isinstance(value, dict) and '$lte' in value:
                if current is None or current > value['$lte']:
                    return False
            elif current != value:
                return False
        return True

    async def find_one(self, query, *, sort=None):
        await asyncio.sleep(0)
        matches = [doc for doc in self.docs if self.matches(doc, query)]
        for key, direction in reversed(sort or []):
            matches.sort(key=lambda doc: doc[key], reverse=direction == -1)
        return deepcopy(matches[0]) if matches else None

    async def insert_one(self, doc):
        if any(item.get('_id') == doc['_id'] for item in self.docs):
            raise DuplicateKeyError('duplicate')
        self.docs.append(deepcopy(doc))

    async def update_one(self, query, update, *, upsert=False):
        doc = next((item for item in self.docs if self.matches(item, query)), None)
        if doc is None and upsert:
            doc = dict(query)
            self.docs.append(doc)
        if doc is not None:
            await self.find_one_and_update(query, update, return_document=True)

    async def delete_one(self, query):
        doc = next((item for item in self.docs if self.matches(item, query)), None)
        if doc is not None:
            self.docs.remove(doc)

    async def find_one_and_update(self, query, update, *, return_document):
        doc = next((item for item in self.docs if self.matches(item, query)), None)
        if doc is None:
            return None
        for key, value in update['$set'].items():
            parent = doc
            parts = key.split('.')
            for part in parts[:-1]:
                parent = parent[part]
            parent[parts[-1]] = value
        return deepcopy(doc)


class ApprovedVisualRunTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = {
            'testcases': CollectionDouble(
                {'project_id': 'P1', 'testcase_id': 'TC1', 'scenario_id': 'SC1', 'status': 'ready'},
                {'project_id': 'P2', 'testcase_id': 'TC2', 'scenario_id': 'SC2'},
            ),
            'scenarios': CollectionDouble(
                {'project_id': 'P1', 'scenario_id': 'SC1', 'approved': True, 'story_id': 'ST1'},
            ),
            'stories': CollectionDouble(
                {'project_id': 'P1', 'story_id': 'ST1', 'acceptance_criteria': 'Display Draft saved.'},
            ),
            'environments': CollectionDouble(
                {'project_id': 'P1', 'env_id': 'ENV1', 'base_url': 'https://secret-target.invalid/',
                 'credentials': [{'password': 'fixture-canary'}]},
                {'project_id': 'P2', 'env_id': 'ENV2'},
            ),
            'approved_visual_tests': CollectionDouble(),
            'approved_visual_runs': CollectionDouble(),
            'approved_visual_execution_slots': CollectionDouble(),
            'approved_staging_bindings': CollectionDouble(),
        }
        self.user = {'_id': 'reviewer', 'role': 'ADMIN'}

        async def member(project_id, user):
            if project_id != 'P1':
                raise HTTPException(404)

        async def admin(project_id, user):
            await member(project_id, user)
            if user['role'] != 'ADMIN':
                raise HTTPException(403)

        async def current_user():
            return self.user

        for target, name, value in (
            (routes, 'db', self.db), (routes, 'require_project_member', member),
            (routes, 'require_project_admin', admin),
            (settings, 'features', FeatureFlags(approved_visual_run_admission=True)),
            (settings, 'app_env', 'test'),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user] = current_user
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')
        self.addAsyncCleanup(self.client.aclose)
        self.path = '/projects/P1/approved-visual-runs'

    async def approve(self, **changes):
        response = await self.client.post(self.path + '/testcases/TC1/approve', json={
            'button_label': 'Save draft', 'expected_text': 'Draft saved', **changes,
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def prepare(self):
        approval = await self.approve()
        selection = {'approved_test_version_id': approval['version_id'], 'environment_id': 'ENV1'}
        response = await self.client.post(self.path + '/preview', json=selection)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn('secret-target', response.text)
        self.assertNotIn('fixture-canary', response.text)
        return {**selection, 'preview_digest': response.json()['preview_digest'], 'idempotency_key': 'a' * 32}

    async def staging_request(self):
        approval = await self.approve()
        self.db['environments'].docs[0] = {
            'project_id': 'P1', 'env_id': 'ENV1', 'base_url': 'test.salesforce.com', 'revision': 3,
            'credentials': [{'role': 'qa', 'credential_id': 'c' * 32, 'username': 'username-canary',
                             'password': '', 'password_configured': True}],
            'secret_payload': {'version': 1, 'ciphertext': 'ciphertext-canary'},
        }
        selection = {'approved_test_version_id': approval['version_id'], 'environment_id': 'ENV1', 'application_role': 'qa'}
        preview = await self.client.post(self.path + '/staging-bindings/preview', json=selection)
        self.assertEqual(preview.status_code, 200, preview.text)
        return {**selection, 'binding_digest': preview.json()['binding_digest'], 'idempotency_key': 'd' * 32}

    async def test_staging_binding_pins_metadata_without_dispatch_or_secrets(self):
        request = await self.staging_request()
        first, second = await asyncio.gather(*(self.client.post(self.path + '/staging-bindings', json=request) for _ in range(2)))
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json(), second.json())
        binding = first.json()
        self.assertEqual(binding['target_url'], 'https://test.salesforce.com/')
        self.assertEqual(binding['environment_revision'], 3)
        self.assertEqual(binding['application_role'], 'qa')
        self.assertEqual(binding['credential_id'], 'c' * 32)
        self.assertEqual(binding['approved_test_version_id'], request['approved_test_version_id'])
        self.assertFalse(binding['execution_ready'])
        self.assertEqual(len(self.db['approved_staging_bindings'].docs), 1)
        stored = str(self.db['approved_staging_bindings'].docs)
        self.assertNotIn('username-canary', stored)
        self.assertNotIn('ciphertext-canary', stored)
        self.assertNotIn('password', stored)
        self.assertEqual(self.db['approved_visual_runs'].docs, [])
        self.assertEqual(self.db['approved_visual_execution_slots'].docs, [])
        url = self.path + '/staging-bindings/' + binding['binding_id']
        self.assertEqual((await self.client.get(url)).json()['validation_state'], 'current')
        latest = await self.client.get(self.path + '/staging-bindings/testcases/TC1')
        self.assertEqual(latest.json()['binding'], binding)
        conflict = await self.client.post(self.path + '/staging-bindings', json={**request, 'application_role': 'other'})
        self.assertEqual(conflict.status_code, 409)

    async def test_staging_binding_becomes_stale_after_bound_input_changes(self):
        request = await self.staging_request()
        binding = (await self.client.post(self.path + '/staging-bindings', json=request)).json()
        url = self.path + '/staging-bindings/' + binding['binding_id']
        original = deepcopy(self.db['environments'].docs[0])
        for change in ({'revision': 4}, {'base_url': 'https://test.salesforce.com/login'},
                       {'credentials': []}, {'secret_payload': {'ciphertext': 'rotated'}}):
            self.db['environments'].docs[0] = {**deepcopy(original), **change}
            response = await self.client.get(url)
            self.assertEqual(response.json()['validation_state'], 'stale', response.text)
            self.assertEqual(response.json()['binding'], binding)
        self.db['environments'].docs[0] = original
        self.db['testcases'].docs[0]['status'] = 'edited'
        self.assertEqual((await self.client.get(url)).json()['validation_state'], 'stale')
        self.db['testcases'].docs[0]['status'] = 'ready'
        self.db['stories'].docs[0]['acceptance_criteria'] = 'Changed requirement'
        self.assertEqual((await self.client.get(url)).json()['validation_state'], 'stale')
        self.db['stories'].docs[0]['acceptance_criteria'] = 'Display Draft saved.'
        await self.approve(expected_text='Successor expectation')
        self.assertEqual((await self.client.get(url)).json()['validation_state'], 'stale')
        self.assertEqual((await self.client.post(self.path + '/staging-bindings', json=request)).json(), binding)

    async def test_staging_binding_rejects_unsafe_urls_roles_and_unencrypted_credentials(self):
        request = await self.staging_request()
        selection = {key: request[key] for key in ('approved_test_version_id', 'environment_id', 'application_role')}
        environment = self.db['environments'].docs[0]
        for url in ('http://test.salesforce.com', 'https://test.salesforce.com.evil.test',
                    'https://127.0.0.1', 'https://test.salesforce.com/?token=canary',
                    'https://user:password-canary@test.salesforce.com', 'https://test.salesforce.com/#fragment',
                    'https://test.salesforce.com:bad', 'https://test.salesforce.com/other'):
            environment['base_url'] = url
            response = await self.client.post(self.path + '/staging-bindings/preview', json=selection)
            self.assertEqual(response.status_code, 422, response.text)
            self.assertNotIn('password-canary', response.text)
        environment['base_url'] = 'https://test.salesforce.com/'
        self.assertEqual((await self.client.post(self.path + '/staging-bindings/preview', json={**selection, 'application_role': 'foreign'})).status_code, 422)
        environment.pop('secret_payload')
        self.assertEqual((await self.client.post(self.path + '/staging-bindings/preview', json=selection)).status_code, 409)
        self.assertEqual(self.db['approved_staging_bindings'].docs, [])

    async def test_staging_binding_scope_gates_and_no_synthetic_start(self):
        request = await self.staging_request()
        binding = (await self.client.post(self.path + '/staging-bindings', json=request)).json()
        url = self.path + '/staging-bindings/' + binding['binding_id']
        self.assertEqual((await self.client.get(url.replace('/P1/', '/P2/'))).status_code, 404)
        self.assertEqual((await self.client.post(self.path.replace('/P1/', '/P2/') + '/staging-bindings', json=request)).status_code, 404)
        for extra in ({'url': 'https://external.test'}, {'password': 'input-canary'}, {'command': 'anything'}):
            rejected = await self.client.post(self.path + '/staging-bindings', json={**request, **extra})
            self.assertEqual(rejected.status_code, 422)
            self.assertNotIn('input-canary', rejected.text)
        with patch.object(settings.features, 'approved_visual_run_execution', True), \
             patch.object(settings, 'browserstack_username', 'fixture-user'), \
             patch.object(settings, 'browserstack_access_key', 'fixture-key'):
            self.assertEqual((await self.client.post(self.path + '/' + binding['binding_id'] + '/start')).status_code, 404)
        self.assertEqual(self.db['approved_visual_execution_slots'].docs, [])
        settings.features.approved_visual_run_admission = False
        self.assertEqual((await self.client.get(url)).status_code, 403)
        settings.features.approved_visual_run_admission = True
        settings.app_env = 'production'
        self.assertEqual((await self.client.get(url)).status_code, 403)

    async def test_staging_binding_rejects_stale_preview_before_insert(self):
        request = await self.staging_request()
        self.db['environments'].docs[0]['revision'] += 1
        response = await self.client.post(self.path + '/staging-bindings', json=request)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.db['approved_staging_bindings'].docs, [])

    async def test_concurrent_admission_pins_inputs_and_returns_one_record(self):
        request = await self.prepare()
        first, second = await asyncio.gather(*(self.client.post(self.path, json=request) for _ in range(2)))
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(first.json(), second.json())
        run = first.json()
        self.assertEqual(run['state'], 'admitted')
        self.assertIsNone(run['verdict'])
        self.assertEqual(run['test']['version_id'], request['approved_test_version_id'])
        self.assertEqual(run['test']['knowledge_version'], 'synthetic-fixture-knowledge-v1')
        self.assertEqual(run['target'], 'server-owned-synthetic-fixture')
        self.assertEqual(len(self.db['approved_visual_runs'].docs), 1)
        self.assertNotIn('fixture-canary', str(self.db['approved_visual_runs'].docs))
        self.assertEqual(self.db['approved_visual_tests'].docs[0]['acceptance_criteria_snapshot'],
                         'Display Draft saved.')
        conflict = await self.client.post(self.path, json={**request, 'preview_digest': 'b' * 64})
        self.assertEqual(conflict.status_code, 409)

    async def test_stale_environment_and_superseded_approval_reject_before_insert(self):
        request = await self.prepare()
        self.db['environments'].docs[0]['base_url'] = 'https://changed.invalid/'
        self.assertEqual((await self.client.post(self.path, json=request)).status_code, 409)
        await self.approve(expected_text='Updated draft saved')
        self.assertEqual((await self.client.post(self.path, json=request)).status_code, 409)
        self.assertEqual(self.db['approved_visual_runs'].docs, [])

    async def test_story_edit_invalidates_approval(self):
        request = await self.prepare()
        self.db['stories'].docs[0]['acceptance_criteria'] = 'Changed expectation.'
        self.assertEqual((await self.client.post(self.path, json=request)).status_code, 409)
        self.assertEqual(self.db['approved_visual_runs'].docs, [])

    async def test_status_and_cancel_are_scoped_and_cancellation_is_idempotent(self):
        request = await self.prepare()
        admitted = (await self.client.post(self.path, json=request)).json()
        url = self.path + '/' + admitted['run_id']
        other = url.replace('/P1/', '/P2/')
        self.assertEqual((await self.client.get(other)).status_code, 404)
        self.assertEqual((await self.client.post(other + '/cancel')).status_code, 404)
        self.assertEqual((await self.client.get(url)).json(), admitted)
        overview = await self.client.get(self.path + '/testcases/TC1')
        self.assertEqual(overview.json()['latest_run'], admitted)
        self.assertEqual(overview.json()['approval']['version_id'], admitted['test']['version_id'])
        cancelled = (await self.client.post(url + '/cancel')).json()
        self.assertEqual((cancelled['state'], cancelled['verdict']), ('cancelled', 'cancelled'))
        self.assertEqual((await self.client.post(url + '/cancel')).json(), cancelled)
        self.assertEqual((await self.client.post(self.path, json=request)).json(), cancelled)
        self.assertEqual((await self.client.get(url)).json(), cancelled)
        self.assertEqual((await self.client.get(self.path + '/testcases/TC1')).json()['latest_run'], cancelled)

    async def test_start_persists_result_and_project_scopes_evidence(self):
        request = await self.prepare()
        admitted = (await self.client.post(self.path, json=request)).json()
        url = self.path + '/' + admitted['run_id']
        self.assertEqual((await self.client.post(url + '/start')).status_code, 403)
        settings.features.approved_visual_run_execution = True
        remote_started = asyncio.Event()
        remote_finish = asyncio.Event()

        class Remote:
            cleanup_confirmed = True

            def __init__(self, username, key):
                pass

            async def execute(self, label, expected, checkpoint):
                await checkpoint()
                remote_started.set()
                await remote_finish.wait()
                return 'passed', 'Draft saved', b'fixture-image', None

            async def close(self):
                pass

        async def member(project_id, user):
            self.assertEqual(project_id, 'P1')

        worker = routes.approved_visual_execution
        with patch.object(settings, 'browserstack_username', 'fixture'), \
             patch.object(settings, 'browserstack_access_key', 'fixture'), \
             patch.object(worker, 'require_project_member', member), \
             patch.dict(sys.modules, {'app.services.synthetic_visual_browser': SimpleNamespace(RemoteSyntheticBrowser=Remote)}):
            response = await self.client.post(url + '/start')
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(response.json()['state'], 'running')
            try:
                await asyncio.wait_for(remote_started.wait(), timeout=2)
                other = await self.client.post(self.path, json={**request, 'idempotency_key': 'b' * 32})
                other_url = self.path + '/' + other.json()['run_id']
                self.assertEqual((await self.client.post(other_url + '/start')).status_code, 409)
            finally:
                remote_finish.set()
                await asyncio.gather(*tuple(worker.tasks))
            remote_started.clear()
            remote_finish.clear()
            self.assertEqual((await self.client.post(other_url + '/start')).status_code, 202)
            try:
                await asyncio.wait_for(remote_started.wait(), timeout=2)
                self.assertEqual((await self.client.post(other_url + '/cancel')).json()['state'], 'cancelling')
            finally:
                remote_finish.set()
                await asyncio.gather(*tuple(worker.tasks))
            cancelled = (await self.client.get(other_url)).json()
            self.assertEqual((cancelled['state'], cancelled['verdict']), ('cancelled', 'cancelled'))
        result = (await self.client.get(url)).json()
        self.assertEqual((result['state'], result['verdict'], result['observed_text']), ('completed', 'passed', 'Draft saved'))
        image = await self.client.get(url + '/evidence')
        self.assertEqual((image.status_code, image.content, image.headers['cache-control']),
                         (200, b'fixture-image', 'no-store'))
        self.assertEqual((await self.client.get(url.replace('/P1/', '/P2/') + '/evidence')).status_code, 404)
        self.assertEqual(self.db['approved_visual_execution_slots'].docs, [])

    async def test_rejects_foreign_resources_and_untrusted_input(self):
        request = await self.prepare()
        foreign_approval = deepcopy(self.db['approved_visual_tests'].docs[0])
        foreign_approval.update({'_id': 'f' * 32, 'project_id': 'P2'})
        self.db['approved_visual_tests'].docs.append(foreign_approval)
        for payload, expected in (
            ({**request, 'environment_id': 'ENV2'}, 404),
            ({**request, 'approved_test_version_id': 'f' * 32}, 404),
            ({**request, 'url': 'https://external.invalid/'}, 422),
            ({**request, 'command': 'anything'}, 422),
        ):
            self.assertEqual((await self.client.post(self.path, json=payload)).status_code, expected)
        self.assertEqual((await self.client.post(self.path.replace('P1', 'P2'), json=request)).status_code, 404)
        self.assertEqual(self.db['approved_visual_runs'].docs, [])

    async def test_approval_requires_admin_and_explicit_expectation(self):
        path = self.path + '/testcases/TC1/approve'
        self.assertEqual((await self.client.post(path, json={'button_label': 'Save'})).status_code, 422)
        self.user['role'] = 'TESTER'
        response = await self.client.post(path, json={'button_label': 'Save', 'expected_text': 'Saved'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db['approved_visual_tests'].docs, [])

    async def test_disabled_and_production_mode_reject_before_writes(self):
        path = self.path + '/testcases/TC1/approve'
        payload = {'button_label': 'Save', 'expected_text': 'Saved'}
        settings.features.approved_visual_run_admission = False
        self.assertEqual((await self.client.post(path, json=payload)).status_code, 403)
        settings.features.approved_visual_run_admission = True
        settings.app_env = 'production'
        self.assertEqual((await self.client.post(path, json=payload)).status_code, 403)
        self.assertEqual(self.db['approved_visual_tests'].docs, [])
