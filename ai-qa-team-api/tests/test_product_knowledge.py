"""Synthetic ASGI/auth/database/provider checks; no real AI or Mongo calls."""
import os
import json
import unittest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

import httpx
from fastapi import FastAPI, HTTPException

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "knowledge_tests",
                            "REDIS_HOST": "localhost", "REDIS_PORT": "6399", "REDIS_USERNAME": "",
                            "REDIS_PASSWORD": "", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from app.config import settings, FeatureFlags
    from app.routes import product_knowledge_routes as routes
    from app.services.product_knowledge import ProductKnowledge
    from app.services.knowledge_test_design import KnowledgeTestDesign
    from app.models.product_knowledge import KnowledgeSourceInput, KnowledgeDraft
    from app.services.ai.ai_usage_policy import AIOperation, get_ai_usage_policy
    from test_visual_specifications import Collection


class KnowledgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = {key: Collection() for key in ("product_knowledge_sources", "product_knowledge_versions", "story_analyses", "prompt_definitions")}
        self.db["stories"] = Collection({"project_id": "P1", "story_id": "ST1", "title": "Save draft",
                                        "description": "Synthetic", "acceptance_criteria": "Show Draft saved.", "out_of_scope": ""})
        self.usage = SimpleNamespace(execute=AsyncMock())
        self.service = ProductKnowledge(self.db, self.usage)
        self.user = {"_id": "reviewer", "role": "ADMIN"}
        async def member(project, user):
            if project != "P1": raise HTTPException(404)
        async def admin(project, user):
            await member(project, user)
            if user["role"] != "ADMIN": raise HTTPException(403)
        for target, key, value in ((routes, "db", self.db), (routes, "service", lambda: self.service),
                                  (routes, "require_project_member", member), (routes, "require_project_admin", admin),
                                  (settings, "features", FeatureFlags(product_knowledge=True, story_analysis=True, scenario_generation=True, test_generation=True))):
            patcher = patch.object(target, key, value); patcher.start(); self.addCleanup(patcher.stop)
        app = FastAPI(); app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user] = lambda: self.user
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.base = "/projects/P1/knowledge"

    async def approved(self):
        source = await self.service.add_source("P1", "reviewer", KnowledgeSourceInput(title="Guide", kind="document", text="Show Draft saved."))
        self.claim = {"claim_id": "K1", "category": "business_rule", "statement": "Show Draft saved.",
                      "epistemic_status": "expected", "source_id": source["source_id"], "segment_index": None, "quote": "Show Draft saved."}
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Rules", claims=[self.claim]))
        return await self.service.approve("P1", "reviewer", draft["version_id"])

    async def analysis(self, findings=None):
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"summary": "Review save behavior", "findings": findings or []}))
        return await self.service.analyze("P1", self.user, "ST1")

    async def test_project_and_feature_guards_and_safe_validation(self):
        self.assertEqual((await self.client.get("/projects/P2/knowledge")).status_code, 404)
        settings.features.product_knowledge = False
        self.assertEqual((await self.client.post(self.base + "/sources", json={})).status_code, 403)
        settings.features.product_knowledge = True
        response = await self.client.post(self.base + "/sources", json={"title": "x", "kind": "document", "text": "", "secret": "CANARY"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("CANARY", response.text)

    async def test_citations_approval_successors_and_cross_project_source(self):
        approved = await self.approved()
        self.user["role"] = "MEMBER"
        self.assertEqual((await self.client.post(self.base + f'/versions/{approved["version_id"]}/approve')).status_code, 403)
        wrong = {**self.claim, "quote": "invented"}
        response = await self.client.post(self.base + "/versions", json={"title": "wrong", "claims": [wrong]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual((await self.client.post("/projects/P2/knowledge/versions", json={"title": "wrong", "claims": [self.claim]})).status_code, 404)
        self.claim["statement"] = "Updated expectation"
        successor = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Updated", claims=[self.claim], parent_version_id=approved["version_id"]))
        await self.service.approve("P1", "reviewer", successor["version_id"])
        original = await self.service.record("product_knowledge_versions", "P1", approved["version_id"])
        self.assertEqual(original["claims"][0]["statement"], "Show Draft saved.")
        self.assertEqual((await self.service.active("P1"))["version_id"], successor["version_id"])

    async def test_blockers_require_review_and_changes_invalidate_context(self):
        await self.approved()
        finding = {"finding_id": "F1", "category": "ambiguity", "severity": "blocker", "description": "When?", "question": "When should it appear?", "criterion_quote": "Draft saved", "knowledge_claim_id": "K1"}
        analysis = await self.analysis([finding])
        self.assertEqual((await self.client.post(self.base + f'/stories/ST1/analysis/{analysis["analysis_id"]}/review', json={"resolutions": []})).status_code, 422)
        with self.assertRaises(HTTPException): await self.service.generation_context("P1", "ST1")
        response = await self.client.post(self.base + f'/stories/ST1/analysis/{analysis["analysis_id"]}/review', json={"resolutions": [{"finding_id": "F1", "decision": "clarified", "rationale": "After Save is clicked."}]})
        self.assertEqual(response.status_code, 200, response.text)
        await self.service.generation_context("P1", "ST1")
        self.db["stories"].docs[0]["acceptance_criteria"] = "Changed expected behavior"
        with self.assertRaises(HTTPException): await self.service.generation_context("P1", "ST1")
        self.assertTrue((await self.service.latest_analysis("P1", "ST1"))["stale"])

    async def test_metered_extraction_validates_exact_transcript_segment(self):
        source = await self.service.add_source("P1", "reviewer", KnowledgeSourceInput(title="Demo", kind="recording_transcript", segments=[{"start_seconds": 10, "end_seconds": 15, "text": "Show Draft saved."}]))
        claim = {"claim_id": "K1", "category": "workflow", "statement": "Saved", "epistemic_status": "observed", "source_id": source["source_id"], "segment_index": 0, "quote": "Draft saved"}
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"claims": [claim], "clarification_questions": ["Is this expected?"]}))
        result = await self.service.extract("P1", self.user, source["source_id"])
        self.assertEqual(result.claims[0].epistemic_status, "observed")
        self.assertEqual(self.usage.execute.call_args.args[0], AIOperation.KNOWLEDGE_EXTRACTION)
        self.assertEqual(self.usage.execute.call_args.args[3].prompt_version, "CODE_DEFAULT_V1")
        self.db["prompt_definitions"].docs.append({
            "prompt_key": "KNOWLEDGE_EXTRACTION_V1", "active_version": 2,
            "versions": [{"version": 2, "status": "ACTIVE", "system_prompt": "Preserve product terminology."}]})
        await self.service.extract("P1", self.user, source["source_id"])
        request = self.usage.execute.call_args.args[3]
        self.assertEqual(request.prompt_version, "2")
        self.assertIn("Preserve product terminology.", request.system_prompt)
        self.assertIn("untrusted data", request.system_prompt)
        claim["segment_index"] = 1
        self.usage.execute.return_value.text = json.dumps({"claims": [claim], "clarification_questions": []})
        with self.assertRaises(HTTPException): await self.service.extract("P1", self.user, source["source_id"])

    async def test_scenario_design_returns_distinct_intent_not_procedure(self):
        approved = await self.approved(); analysis = await self.analysis()
        from app.models.product_knowledge import ReviewStoryAnalysis
        await self.service.review_analysis("P1", "reviewer", "ST1", analysis["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        intent = {"title": "Save", "description": "Save a draft", "purpose": "Confirm save", "role": None, "coverage_type": "happy_path", "preconditions": [], "expected_outcome": "Show Draft saved.", "acceptance_criteria_refs": ["Show Draft saved."], "rule_references": ["K1"]}
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"scenarios": [intent]}))
        plans, context = await KnowledgeTestDesign(self.db, self.usage).scenarios("P1", self.user, await self.service.story("P1", "ST1"), 3, "basic")
        self.assertEqual(len(plans), 1)  # fewer supported intents are valid, never fabricate three
        self.assertNotIn("steps", plans[0]); self.assertEqual(context["knowledge"]["version_id"], approved["version_id"])
        self.usage.execute.return_value.text = json.dumps({"scenarios": [intent, intent]})
        with self.assertRaises(HTTPException): await KnowledgeTestDesign(self.db, self.usage).scenarios("P1", self.user, await self.service.story("P1", "ST1"), 3, "basic")

    async def test_detailed_case_design_has_assertions_and_rejects_stale_scenario(self):
        approved = await self.approved(); analysis = await self.analysis()
        from app.models.product_knowledge import ReviewStoryAnalysis
        await self.service.review_analysis("P1", "reviewer", "ST1", analysis["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        scenario = {"_id": object(), "project_id": "P1", "story_id": "ST1", "scenario_id": "SC1", "title": "Save",
                    "knowledge_version_id": approved["version_id"], "story_analysis_id": analysis["analysis_id"]}
        case = {"title": "Save a draft", "purpose": "Verify persistence notification", "preconditions": [], "public_data": [],
                "procedure": [{"instruction": "Click Save", "expected": "Draft saved"}], "assertions": ["Draft saved"],
                "cleanup": [], "acceptance_criteria_refs": ["Show Draft saved."], "rule_references": ["K1"]}
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"testcases": [case]}))
        cases, _ = await KnowledgeTestDesign(self.db, self.usage).testcases("P1", self.user, scenario, 2)
        self.assertEqual(cases[0]["procedure"][0]["expected"], "Draft saved")
        self.assertEqual(cases[0]["assertions"], ["Draft saved"])
        self.assertNotIn("_id", json.loads(self.usage.execute.call_args.args[3].prompt)["scenario"])
        scenario["knowledge_version_id"] = "f" * 32
        with self.assertRaises(HTTPException): await KnowledgeTestDesign(self.db, self.usage).testcases("P1", self.user, scenario, 1)

    async def test_specification_pins_knowledge_and_rule_change_requires_review(self):
        approved = await self.approved(); analysis = await self.analysis()
        from app.models.product_knowledge import ReviewStoryAnalysis
        from app.models.visual_specification import SpecificationDraft, SpecificationPreviewSelection
        from app.services.visual_specifications import VisualSpecifications
        await self.service.review_analysis("P1", "reviewer", "ST1", analysis["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        settings.features.reusable_workflows = True
        self.db.update({"visual_workflow_versions": Collection(), "visual_test_spec_versions": Collection(),
            "testcases": Collection({"project_id": "P1", "testcase_id": "TC1", "scenario_id": "SC1"}),
            "scenarios": Collection({"project_id": "P1", "scenario_id": "SC1", "story_id": "ST1", "approved": True}),
            "environments": Collection({"project_id": "P1", "env_id": "ENV1", "revision": 1, "base_url": "https://test.salesforce.com", "credentials": []})})
        service = VisualSpecifications(self.db, b"test")
        draft = await service.create_specification("P1", "TC1", "reviewer", SpecificationDraft(steps=[{"action": "assert_text", "expected": "Draft saved"}]))
        await service.approve_specification("P1", "TC1", "reviewer", draft["version_id"])
        preview = await service.preview("P1", "TC1", draft["version_id"], SpecificationPreviewSelection(environment_id="ENV1"))
        self.assertEqual(preview.knowledge_version_id, approved["version_id"])
        self.assertEqual(preview.story_analysis_id, analysis["analysis_id"])
        self.claim["statement"] = "Save notification changed"
        next_draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Changed", claims=[self.claim]))
        await self.service.approve("P1", "reviewer", next_draft["version_id"])
        state = await service.latest_specification("P1", "TC1")
        self.assertTrue(state["review_required"])
        self.assertEqual(state["version"]["knowledge_version_id"], approved["version_id"])
        self.assertEqual(state["version"]["status"], "approved")

    def test_all_supported_ai_tasks_have_bounded_policies(self):
        for operation in AIOperation:
            policy = get_ai_usage_policy(operation)
            self.assertGreater(policy.credit_cost, 0)
            self.assertGreater(policy.max_input_chars, 0)
            self.assertGreater(policy.max_output_tokens, 0)
