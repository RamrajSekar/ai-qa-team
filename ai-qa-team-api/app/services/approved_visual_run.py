"""Resolve approved synthetic inputs and durably admit a run without dispatch."""
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
from uuid import uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models.approved_visual_run import AdmittedVisualRun, ApprovedVisualPreview, ApprovedVisualTest, VisualTestRunState


def digest(value, key=None):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()
    return hmac.new(key, data, sha256).hexdigest() if key is not None else sha256(data).hexdigest()


class ApprovedVisualRuns:
    def __init__(self, db, environment_digest_key):
        self.db = db
        self.environment_digest_key = environment_digest_key

    @staticmethod
    def approval_head(project_id, testcase_id):
        return {'_id': 'head:' + digest([project_id, testcase_id]), 'project_id': project_id}

    async def source(self, project_id, testcase_id):
        scope = {'project_id': project_id}
        testcase = await self.db['testcases'].find_one({**scope, 'testcase_id': testcase_id})
        if not testcase:
            raise HTTPException(404, 'Test case not found.')
        scenario = await self.db['scenarios'].find_one({**scope, 'scenario_id': testcase.get('scenario_id')})
        if not scenario or scenario.get('approved') is not True or not scenario.get('story_id'):
            raise HTTPException(409, 'An approved scenario linked to a story is required.')
        story = await self.db['stories'].find_one({**scope, 'story_id': scenario['story_id']})
        criteria = (story or {}).get('acceptance_criteria')
        if not isinstance(criteria, str) or not criteria.strip():
            raise HTTPException(409, 'Story acceptance criteria are required.')
        return story['story_id'], scenario['scenario_id'], criteria, digest([testcase, scenario, story])

    async def approve(self, project_id, testcase_id, reviewer, payload):
        story_id, scenario_id, criteria, source_digest = await self.source(project_id, testcase_id)
        test = ApprovedVisualTest(
            **payload.model_dump(), version_id=uuid4().hex, testcase_id=testcase_id,
            story_id=story_id, scenario_id=scenario_id, source_digest=source_digest,
            content_digest=digest([source_digest, 'synthetic-fixture-knowledge-v1', payload.model_dump()]),
            approved_by=reviewer, approved_at=datetime.now(timezone.utc),
        )
        versions = self.db['approved_visual_tests']
        await versions.insert_one({
            '_id': test.version_id, 'project_id': project_id, 'testcase_id': testcase_id,
            'approved_at': test.approved_at, 'acceptance_criteria_snapshot': criteria,
            'test': test.model_dump(mode='json'),
        })
        await versions.update_one(
            self.approval_head(project_id, testcase_id),
            {'$set': {'active_version_id': test.version_id}}, upsert=True,
        )
        return test

    async def preview(self, project_id, selection):
        versions = self.db['approved_visual_tests']
        approval = await versions.find_one({'project_id': project_id, '_id': selection.approved_test_version_id})
        environment = await self.db['environments'].find_one({
            'project_id': project_id, 'env_id': selection.environment_id,
        })
        if not approval or not environment:
            raise HTTPException(404, 'Approved test or environment not found.')
        test = ApprovedVisualTest.model_validate_json(json.dumps(approval['test']))
        head = await versions.find_one(self.approval_head(project_id, test.testcase_id))
        _, _, _, current_digest = await self.source(project_id, test.testcase_id)
        if not head or head['active_version_id'] != test.version_id or current_digest != test.source_digest:
            raise HTTPException(409, 'Approval is stale. Review and approve the test again.')
        environment_digest = digest(environment, self.environment_digest_key)
        return ApprovedVisualPreview(
            test=test, environment_id=selection.environment_id, environment_digest=environment_digest,
            preview_digest=digest([project_id, test.version_id, test.content_digest, environment_digest,
                                   'approved-visual-synthetic-v1']),
        )

    async def admit(self, project_id, requester, payload):
        runs = self.db['approved_visual_runs']
        run_id = digest([project_id, requester, payload.idempotency_key])
        request_digest = digest(payload.model_dump())
        query = {'_id': run_id, 'project_id': project_id}
        existing = await runs.find_one(query)
        if existing:
            return self.replay(existing, request_digest)
        preview = await self.preview(project_id, payload)
        if not hmac.compare_digest(preview.preview_digest, payload.preview_digest):
            raise HTTPException(409, 'Preview inputs changed. Preview the run again.')
        run = AdmittedVisualRun(run_id=run_id, **preview.model_dump())
        try:
            await runs.insert_one({
                **query, 'request_digest': request_digest, 'requested_by': requester,
                'admitted_at': datetime.now(timezone.utc), 'run': run.model_dump(mode='json'),
            })
        except DuplicateKeyError:
            existing = await runs.find_one(query)
            if not existing:
                raise
            return self.replay(existing, request_digest)
        return run

    async def testcase_state(self, project_id, testcase_id):
        if not await self.db['testcases'].find_one({'project_id': project_id, 'testcase_id': testcase_id}):
            raise HTTPException(404, 'Test case not found.')
        versions = self.db['approved_visual_tests']
        head = await versions.find_one(self.approval_head(project_id, testcase_id))
        approval = None
        if head:
            doc = await versions.find_one({'project_id': project_id, '_id': head['active_version_id']})
            if doc:
                approval = ApprovedVisualTest.model_validate_json(json.dumps(doc['test']))
        latest = await self.db['approved_visual_runs'].find_one(
            {'project_id': project_id, 'run.test.testcase_id': testcase_id},
            sort=[('admitted_at', -1), ('_id', -1)],
        )
        latest_run = self.read_run(latest) if latest else None
        if latest_run and latest_run.state in {'running', 'cancelling'}:
            latest_run = await self.status(project_id, latest_run.run_id)
        return VisualTestRunState(approval=approval, latest_run=latest_run)

    async def status(self, project_id, run_id):
        runs = self.db['approved_visual_runs']
        query = {'project_id': project_id, '_id': run_id}
        doc = await runs.find_one(query)
        if not doc:
            raise HTTPException(404, 'Run not found.')
        if doc['run']['state'] in {'running', 'cancelling'}:
            previous = doc['run']['state']
            updated = await runs.find_one_and_update(
                {**query, 'run.state': previous, 'execution_expires_at': {'$lte': datetime.now(timezone.utc)}},
                {'$set': {'run.state': 'cancelled' if previous == 'cancelling' else 'completed',
                          'run.verdict': 'cancelled' if previous == 'cancelling' else 'blocked',
                          'run.reason': 'EXECUTION_INTERRUPTED'}},
                return_document=ReturnDocument.AFTER,
            )
            doc = updated or doc
        return self.read_run(doc)

    async def cancel(self, project_id, run_id):
        doc = await self.db['approved_visual_runs'].find_one_and_update(
            {'project_id': project_id, '_id': run_id, 'run.state': 'admitted'},
            {'$set': {'run.state': 'cancelled', 'run.verdict': 'cancelled',
                      'cancelled_at': datetime.now(timezone.utc)}},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            doc = await self.db['approved_visual_runs'].find_one_and_update(
                {'project_id': project_id, '_id': run_id, 'run.state': 'running'},
                {'$set': {'run.state': 'cancelling'}}, return_document=ReturnDocument.AFTER,
            )
        return self.read_run(doc) if doc else await self.status(project_id, run_id)

    @staticmethod
    def read_run(doc):
        return AdmittedVisualRun.model_validate_json(json.dumps(doc['run']))

    @staticmethod
    def replay(existing, request_digest):
        if existing['request_digest'] != request_digest:
            raise HTTPException(409, 'Idempotency key was used with different inputs.')
        return ApprovedVisualRuns.read_run(existing)
