"""Phase 1 review/export with synthetic auth/Mongo. No provider or browser calls."""
import asyncio
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "design_tests", "REDIS_HOST": "localhost",
                            "REDIS_PORT": "6399", "REDIS_USERNAME": "", "REDIS_PASSWORD": "", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from app.config import settings, FeatureFlags
    from app.routes import test_design_routes as routes
    from app.services.approved_visual_run import digest
    from test_visual_specifications import Collection


class TestDesignReviewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.story = {"story_id": "ST1", "title": "Save draft", "description": "Synthetic", "acceptance_criteria": "Show Draft saved.", "out_of_scope": ""}
        knowledge = {"_id": "a" * 32, "version_id": "a" * 32, "project_id": "P1", "status": "approved", "approved_at": "2026-11-11T00:00:00Z",
            "content_digest": "b" * 64, "claims": [{"claim_id": "K1", "statement": "Show Draft saved.", "epistemic_status": "expected"}]}
        analysis = {"_id": "c" * 32, "analysis_id": "c" * 32, "project_id": "P1", "story_id": "ST1", "created_at": "2026-11-11T00:00:00Z",
            "status": "reviewed", "story_digest": digest(self.story), "knowledge_version_id": "a" * 32, "findings": [], "resolutions": []}
        self.db = {"test_design_documents": Collection(), "testcases": Collection({"_id": "case", "project_id": "P1", "testcase_id": "TC1", "scenario_id": "SC1", "title": "Save", "knowledge_version_id": "a" * 32}),
            "scenarios": Collection({"project_id": "P1", "scenario_id": "SC1", "story_id": "ST1", "approved": True, "title": "Save draft", "knowledge_version_id": "a" * 32}),
            "stories": Collection({**self.story, "project_id": "P1"}), "product_knowledge_versions": Collection(knowledge), "story_analyses": Collection(analysis)}
        self.user = {"_id": "reviewer", "role": "ADMIN"}
        async def member(project, user):
            if project != "P1": raise HTTPException(404)
        async def admin(project, user):
            await member(project, user)
            if user["role"] != "ADMIN": raise HTTPException(403)
        for target, key, value in ((routes, "db", self.db), (routes, "require_project_member", member), (routes, "require_project_admin", admin),
            (settings, "features", FeatureFlags(test_generation=True, product_knowledge=True, story_analysis=True))):
            patcher = patch.object(target, key, value); patcher.start(); self.addCleanup(patcher.stop)
        app = FastAPI(); app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user] = lambda: self.user
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.base = "/projects/P1/test-design/cases/TC1"
        self.case = {"title": "Save a draft", "purpose": "Verify save confirmation", "role": None, "preconditions": [], "public_data": [],
            "procedure": [{"instruction": "Click Save draft", "expected": "Draft saved"}], "assertions": ["Draft saved appears"], "cleanup": [],
            "acceptance_criteria_refs": ["Show Draft saved."], "rule_references": ["K1"]}

    async def draft(self, key="1" * 32, **fields):
        response = await self.client.post(self.base, json={"case": self.case, "idempotency_key": key, **fields})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def approve(self, version):
        response = await self.client.post(self.base + "/" + version["version_id"] + "/approve")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_standalone_approval_and_manual_exports_need_no_execution(self):
        version = await self.draft()
        self.assertEqual((await self.client.get(self.base + f'/{version["version_id"]}/export')).status_code, 409)
        approved = await self.approve(version)
        for format in ("json", "text"):
            response = await self.client.get(self.base + f'/{version["version_id"]}/export?format={format}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "private, no-store")
            self.assertIn("Draft saved", response.json()["content"])
        state = (await self.client.get(self.base)).json()
        self.assertFalse(state["review_required"])
        self.assertEqual(state["active_version_id"], approved["version_id"])
        self.assertEqual(set(self.db), {"test_design_documents", "testcases", "scenarios", "stories", "product_knowledge_versions", "story_analyses"})

    async def test_project_admin_and_feature_guards(self):
        version = await self.draft()
        self.user["role"] = "TESTER"
        self.assertEqual((await self.client.post(self.base + f'/{version["version_id"]}/approve')).status_code, 403)
        foreign = "/projects/P2/test-design/cases/TC1"
        for method, path in (("GET", foreign), ("POST", foreign + f'/{version["version_id"]}/approve'), ("GET", foreign + f'/{version["version_id"]}/export')):
            self.assertEqual((await self.client.request(method, path)).status_code, 404)
        settings.features.product_knowledge = False
        self.assertEqual((await self.client.get(self.base)).status_code, 403)

    async def test_missing_or_blank_expectations_and_wrong_references_reject(self):
        for field, invalid in (("assertions", []), ("assertions", ["   "]), ("procedure", [{"instruction": "Save", "expected": ""}])):
            payload = {**self.case, field: invalid}
            response = await self.client.post(self.base, json={"case": payload, "idempotency_key": "1" * 32, "secret": "CANARY"})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("CANARY", response.text)
        response = await self.client.post(self.base, json={"case": {**self.case, "rule_references": ["invented"]}, "idempotency_key": "1" * 32})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db["test_design_documents"].docs, [])

    async def test_concurrent_idempotent_saves_create_one_snapshot(self):
        payload = {"case": self.case, "idempotency_key": "1" * 32}
        responses = await asyncio.gather(self.client.post(self.base, json=payload), self.client.post(self.base, json=payload))
        self.assertEqual([item.status_code for item in responses], [201, 201])
        self.assertEqual(responses[0].json()["version_id"], responses[1].json()["version_id"])
        self.assertEqual(len(self.db["test_design_documents"].docs[0]["versions"]), 1)
        changed = {**payload, "case": {**self.case, "title": "Changed"}}
        self.assertEqual((await self.client.post(self.base, json=changed)).status_code, 409)

    async def test_successors_and_concurrent_approval_preserve_prior_approval(self):
        original = await self.approve(await self.draft())
        self.case["title"] = "Reviewed correction"
        first = await self.draft("2" * 32)
        second = await self.draft("3" * 32)
        responses = await asyncio.gather(*[self.client.post(self.base + f'/{item["version_id"]}/approve') for item in (first, second)])
        self.assertEqual(sorted(item.status_code for item in responses), [200, 409])
        state = (await self.client.get(self.base)).json()
        old = next(item for item in state["versions"] if item["version_id"] == original["version_id"])
        self.assertEqual(old["case"]["title"], "Save a draft")
        active = state["active_version_id"]
        await self.approve(original)
        self.assertEqual((await self.client.get(self.base)).json()["active_version_id"], active)

    async def test_changed_knowledge_flags_and_requires_explicit_successor_review(self):
        original = await self.approve(await self.draft())
        knowledge = deepcopy(self.db["product_knowledge_versions"].docs[0])
        knowledge.update(_id="d" * 32, version_id="d" * 32, approved_at="2026-11-12T00:00:00Z")
        self.db["product_knowledge_versions"].docs.append(knowledge)
        analysis = deepcopy(self.db["story_analyses"].docs[0])
        analysis.update(_id="e" * 32, analysis_id="e" * 32, knowledge_version_id="d" * 32, created_at="2026-11-12T00:00:00Z")
        self.db["story_analyses"].docs.append(analysis)
        state = (await self.client.get(self.base)).json()
        self.assertTrue(state["review_required"])
        self.assertTrue(state["current_context"]["source_context_changed"])
        self.assertEqual((await self.client.post(self.base, json={"case": self.case, "idempotency_key": "2" * 32})).status_code, 409)
        successor = await self.draft("2" * 32, acknowledge_source_changes=True)
        approved = await self.approve(successor)
        self.assertEqual(approved["context"]["knowledge_version_id"], "d" * 32)
        historical = (await self.client.get(self.base + f'/{original["version_id"]}/export')).json()
        self.assertIn('"stale": true', historical["content"])

    async def test_source_edit_after_draft_blocks_approval(self):
        version = await self.draft()
        self.db["testcases"].docs[0]["title"] = "Material edit"
        self.assertEqual((await self.client.post(self.base + f'/{version["version_id"]}/approve')).status_code, 409)
