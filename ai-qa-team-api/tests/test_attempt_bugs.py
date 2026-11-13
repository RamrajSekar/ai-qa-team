"""Synthetic Mongo, authentication and model doubles; no external requests."""
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import test_manual_results as fixture
from app.services.attempt_bugs import AttemptBugs
from app.services.ai.ai_usage_policy import AIOperation
from app.services import prompt_registry_service
from app.config import settings


class AttemptBugTests(unittest.IsolatedAsyncioTestCase):
    record = fixture.ManualResultTests.record
    create_execution = fixture.ManualResultTests.create_execution

    async def asyncSetUp(self):
        await fixture.ManualResultTests.asyncSetUp(self)
        for name in ('test_attempt_bugs', 'test_bug_proposals', 'prompt_definitions'):
            self.db[name] = fixture.Collection()
        p = patch.object(prompt_registry_service, 'db', self.db)
        p.start(); self.addCleanup(p.stop)
        self.failed = (await self.record(verdict='failed', actual_result='Confirmation absent')).json()
        self.path = self.base + '/attempts/' + self.failed['run_id']

    async def test_draft_and_link_idempotence_version_identity_and_survival_after_pass(self):
        preview = await self.client.get(self.path + '/bugs')
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.headers['cache-control'], 'private, no-store')
        draft = preview.json()['draft']
        self.assertNotIn('PRIVATE_CANARY', str(draft))
        before = deepcopy(self.db['test_results'].docs)
        payload = {'kind': 'draft', 'reviewed': True, 'draft': draft, 'idempotency_key': 'b'*32}
        saved = await self.client.post(self.path + '/bugs', json=payload)
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual(saved.json()['version_id'], self.version['version_id'])
        self.assertEqual(saved.json()['run_id'], self.failed['run_id'])
        self.assertEqual((await self.client.post(self.path + '/bugs', json=payload)).json(), saved.json())
        changed = {**payload, 'draft': {**draft, 'title': 'Changed'}}
        self.assertEqual((await self.client.post(self.path + '/bugs', json=changed)).status_code, 409)
        link = {'kind': 'external', 'reviewed': True, 'url': 'https://bugs.example.test/1', 'idempotency_key': 'c'*32}
        self.assertEqual((await self.client.post(self.path + '/bugs', json=link)).status_code, 201)
        self.assertEqual(before, self.db['test_results'].docs)
        await self.record(idempotency_key='d'*32)
        self.assertEqual(len((await self.client.get(self.path + '/bugs')).json()['links']), 2)

    async def test_url_human_review_project_and_feature_guards(self):
        for url in ['http://bugs.test/1', 'javascript:alert(1)', 'https://user:pass@bugs.test/1', 'https://bugs.test/\\evil']:
            payload = {'kind': 'external', 'reviewed': True, 'url': url, 'idempotency_key': 'b'*32}
            self.assertEqual((await self.client.post(self.path + '/bugs', json=payload)).status_code, 422)
        payload = {'kind': 'external', 'reviewed': False, 'url': 'https://bugs.test/1', 'idempotency_key': 'b'*32}
        self.assertEqual((await self.client.post(self.path + '/bugs', json=payload)).status_code, 422)
        other = self.path.replace('/P1/', '/P2/')
        self.assertEqual((await self.client.get(other + '/bugs')).status_code, 404)
        self.assertEqual((await self.client.post(other + '/bugs', json={**payload, 'reviewed': True})).status_code, 404)
        self.assertEqual((await self.client.post(other + '/bug-draft-ai')).status_code, 404)
        with patch.object(settings.features, 'manual_test_results', False):
            self.assertEqual((await self.client.get(self.path + '/bugs')).status_code, 403)
            self.assertEqual((await self.client.post(self.path + '/bugs', json={**payload, 'reviewed': True})).status_code, 403)
            self.assertEqual((await self.client.post(self.path + '/bug-draft-ai')).status_code, 403)
        passed = (await self.record(idempotency_key='d'*32)).json()
        self.assertEqual((await self.client.get(self.base+'/attempts/'+passed['run_id']+'/bugs')).status_code, 409)

    async def test_explicit_ai_metering_prompt_identity_and_immutable_facts(self):
        usage = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(text='{"summary":"Reported confirmation missing","missing_information":["What is the severity?"]}')))
        result = await AttemptBugs(self.db).draft_ai('P1', self.failed['run_id'], self.user, usage)
        self.assertEqual(usage.execute.call_args.args[0], AIOperation.BUG_REPORT_DRAFT)
        request = usage.execute.call_args.args[3]
        self.assertEqual(request.prompt_key, 'BUG_REPORT_DRAFT_V1')
        self.assertNotIn('PRIVATE_CANARY', request.prompt)
        self.assertEqual(result['draft']['actual_result'], 'Confirmation absent')
        self.assertTrue(result['requires_review'])
        self.assertEqual(self.db['test_attempt_bugs'].docs, [])
        payload = {'kind':'draft','reviewed':True,'draft':result['draft'],'proposal_id':result['proposal_id'],'idempotency_key':'b'*32}
        saved = await self.client.post(self.path+'/bugs', json=payload)
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual(saved.json()['prompt']['prompt_key'], 'BUG_REPORT_DRAFT_V1')

    async def test_invalid_ai_does_not_save_or_expose_raw_output(self):
        from fastapi import HTTPException
        usage = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(text='private-canary-not-json')))
        with self.assertRaises(HTTPException) as failure:
            await AttemptBugs(self.db).draft_ai('P1', self.failed['run_id'], self.user, usage)
        self.assertNotIn('private-canary', str(failure.exception))
        self.assertEqual(self.db['test_bug_proposals'].docs, [])

    async def test_quota_failure_is_safe_and_manual_draft_remains_available(self):
        from app.services.ai.ai_usage_policy import AIUsageError
        with patch.object(AttemptBugs, 'draft_ai', new=AsyncMock(side_effect=AIUsageError('AI_LIMIT_REACHED', 429, 'AI allowance exhausted.'))):
            response = await self.client.post(self.path+'/bug-draft-ai')
        self.assertEqual(response.status_code, 429)
        self.assertEqual((await self.client.get(self.path+'/bugs')).status_code, 200)
        self.assertEqual(self.db['test_attempt_bugs'].docs, [])
