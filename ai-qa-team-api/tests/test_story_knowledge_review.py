"""Combined review fixture tests: no shared DB, AI or browser side effects."""
import asyncio
import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch
from fastapi import HTTPException
import test_product_knowledge as fixtures
from test_requirement_contexts import MongoCollection
from app.models.product_knowledge import KnowledgeDraft
from app.models.story_knowledge_review import StoryKnowledgeReviewInput
from app.services.story_knowledge_review import StoryKnowledgeReview


class StoryChangeTests(unittest.IsolatedAsyncioTestCase):
    async def test_reviewed_missing_detail_can_explicitly_add_knowledge(self):
        from app.models.product_knowledge import ReviewStoryAnalysis
        self.finding.update(category='missing_detail',knowledge_claim_id=None)
        self.usage.execute.return_value=SimpleNamespace(text=json.dumps({'summary':'Details','findings':[self.finding]}))
        self.analysis=await self.service.analyze('P1',self.user,'ST1',analysis_mode='story_only')
        await self.service.review_analysis('P1','reviewer','ST1',self.analysis['analysis_id'],ReviewStoryAnalysis(resolutions=[{'finding_id':'F1','decision':'clarified','rationale':'Navigation is covered separately.'}]))
        payload=self.payload().model_dump()
        payload['decisions'][0].update(action='add',rule_id=None,expected_result='Navigation behavior is specified in separate stories.')
        self.usage.execute.reset_mock()
        row=await self.submit(StoryKnowledgeReviewInput.model_validate(payload))
        await self.changes.approve('P1','ST1',row['review_id'],self.user)
        active=await self.service.active('P1')
        self.assertEqual(len(active['claims']),2)
        self.assertEqual(active['claims'][0]['claim_id'],'K1')
        self.assertTrue(any(c['statement']=='Navigation behavior is specified in separate stories.' for c in active['claims']))
        self.usage.execute.assert_not_called()

    approved = fixtures.KnowledgeTests.approved

    async def asyncSetUp(self):
        await fixtures.KnowledgeTests.asyncSetUp(self)
        for name in ("requirement_contexts", "scenarios", "testcases", "executions"):
            self.db[name] = MongoCollection()
        self.version = await self.approved()
        self.finding = {"finding_id": "F1", "category": "knowledge_conflict", "severity": "blocker",
            "description": "Save behavior changed", "question": "Is removal intended?",
            "criterion_quote": "Show Draft saved.", "knowledge_claim_id": "K1"}
        self.usage.execute.return_value = SimpleNamespace(text=json.dumps({"summary": "Conflict", "findings": [self.finding]}))
        self.analysis = await self.service.analyze("P1", self.user, "ST1", analysis_mode="knowledge_aware")
        self.usage.execute.reset_mock()
        self.changes = StoryKnowledgeReview(self.db)
        self.path = self.base + "/stories/ST1/change-reviews"

    def payload(self, **extra):
        return StoryKnowledgeReviewInput(request_id=uuid4().hex, analysis_id=self.analysis["analysis_id"],
            parent_version_id=self.version["version_id"], decisions=[{"finding_id": "F1", "decision": "intentional_change",
                "action": "replace", "rule_id": "K1", "expected_result": "Save confirmation is no longer shown.", "rationale": "Approved product enhancement."}], **extra)

    async def submit(self, payload=None):
        return await self.changes.submit("P1", "ST1", "member", payload or self.payload())

    async def test_combined_approval_retains_unaffected_rules_history_and_provenance(self):
        extra = {**self.claim, "claim_id": "K2", "statement": "Keep the other behavior."}
        # Establish a two-rule baseline before the analysis.
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Second rule", claims=[extra]))
        self.version = await self.service.approve("P1", "reviewer", draft["version_id"])
        self.analysis = await self.service.analyze("P1", self.user, "ST1", analysis_mode="knowledge_aware")
        self.usage.execute.reset_mock()
        self.db["executions"].docs.append({"_id": "old", "verdict": "Passed"})
        self.db["scenarios"].docs.append({"project_id": "P1", "scenario_id": "SC1", "knowledge_version_id": self.version["version_id"], "approved": True})
        old = deepcopy(self.db["executions"].docs)
        row = await self.submit()
        self.assertEqual((await self.service.active("P1"))["version_id"], self.version["version_id"])
        result = await self.changes.approve("P1", "ST1", row["review_id"], {**self.user, "name": "Alice"})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["approver"]["approved_by_name"], "Alice")
        active = await self.service.active("P1")
        rules = {c["claim_id"]: c for c in active["claims"]}
        self.assertEqual(rules["K2"]["statement"], extra["statement"])
        self.assertEqual(rules["K1"]["statement"], row["changes"][0]["after"])
        source = await self.service.record("product_knowledge_sources", "P1", rules["K1"]["source_id"])
        self.assertEqual(source["origin"]["story_id"], "ST1")
        eligible, excluded = await self.service.analysis_knowledge("P1", "ST1", active)
        self.assertNotIn("K1", [c["claim_id"] for c in eligible["claims"]])
        self.assertTrue(excluded)
        self.assertEqual((await self.service.record("product_knowledge_versions", "P1", self.version["version_id"]))["claims"][0]["statement"], "Show Draft saved.")
        self.assertEqual(self.db["executions"].docs, old)
        self.assertTrue(self.db["scenarios"].docs[0]["requirements_review_required"])
        self.assertTrue(self.db["scenarios"].docs[0]["approved"])
        self.usage.execute.assert_not_called()

    async def test_future_review_requires_explicit_activation_and_retries_keep_approver(self):
        row = await self.submit(self.payload(timing="later", target_release="Release 4"))
        approved = await self.changes.approve("P1", "ST1", row["review_id"], {**self.user, "name": "Alice"})
        self.assertEqual(approved["status"], "approved_pending")
        self.assertEqual((await self.service.active("P1"))["version_id"], self.version["version_id"])
        result = await self.changes.approve("P1", "ST1", row["review_id"], {**self.user, "name": "Bob"}, activate=True)
        self.assertEqual(result["status"], "completed")
        again = await self.changes.approve("P1", "ST1", row["review_id"], {**self.user, "name": "Bob"}, activate=True)
        self.assertEqual(again["approver"]["approved_by_name"], "Alice")
        self.assertEqual((await self.service.active("P1"))["approved_by_name"], "Alice")

    async def test_competing_approvals_only_one_knowledge_successor(self):
        first, second = await self.submit(), await self.submit()
        results = await asyncio.gather(*(self.changes.approve("P1", "ST1", r["review_id"], self.user) for r in (first, second)), return_exceptions=True)
        self.assertEqual(sum(isinstance(r, dict) and r["status"] == "completed" for r in results), 1)
        self.assertEqual(sum(isinstance(r, HTTPException) and r.status_code == 409 for r in results), 1)

    async def test_http_member_submission_admin_approval_project_isolation_and_forgery(self):
        self.user["role"] = "MEMBER"
        response = await self.client.post(self.path, json=self.payload().model_dump())
        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()
        self.assertEqual((await self.client.post(self.path + "/" + row["review_id"] + "/approve")).status_code, 403)
        self.assertEqual((await self.client.get(self.path.replace("P1", "P2"))).status_code, 404)
        self.assertEqual((await self.client.post(self.path, json={**self.payload().model_dump(), "approved_by": "attacker"})).status_code, 422)
        self.user["role"] = "ADMIN"
        self.assertEqual((await self.client.post(self.path + "/" + row["review_id"] + "/approve")).status_code, 200)

    async def test_story_change_and_knowledge_change_require_new_review(self):
        row = await self.submit()
        self.db["stories"].docs[0]["description"] = "Changed story"
        with self.assertRaises(HTTPException) as error:
            await self.changes.approve("P1", "ST1", row["review_id"], self.user)
        self.assertEqual(error.exception.status_code, 409)
        self.assertIsNone(await self.changes.approval(await self.changes.row("P1", "ST1", row["review_id"])))

    async def test_unresolved_decisions_persist_but_cannot_approve(self):
        payload = self.payload().model_dump()
        payload["decisions"] = [{"finding_id": "F1", "decision": "needs_clarification", "rationale": "Ask the owner."}]
        row = await self.submit(StoryKnowledgeReviewInput.model_validate(payload))
        self.assertEqual((await self.changes.listing("P1", "ST1"))["reviews"][0]["review_id"], row["review_id"])
        with self.assertRaises(HTTPException):
            await self.changes.approve("P1", "ST1", row["review_id"], self.user)

    async def test_removal_requires_reason_and_is_explicit_not_an_absence_claim(self):
        payload = self.payload().model_dump()
        payload["decisions"][0]["action"] = "remove"
        row = await self.submit(StoryKnowledgeReviewInput.model_validate(payload))
        await self.changes.approve("P1", "ST1", row["review_id"], self.user)
        active = await self.service.active("P1")
        self.assertEqual(active["claims"], [])
        self.assertEqual(active["removal_reasons"]["K1"], "Approved product enhancement.")

    async def test_uncertain_response_reconciles_without_republishing(self):
        self.db["testcases"].docs.append({"project_id": "P1", "testcase_id": "T1", "rule_references": ["K1"]})
        row = await self.submit()
        with patch.object(self.db["testcases"], "update_one", side_effect=RuntimeError("interrupted")):
            with self.assertRaises(HTTPException) as error:
                await self.changes.approve("P1", "ST1", row["review_id"], self.user)
            self.assertEqual(error.exception.status_code, 503)
        active = await self.service.active("P1")
        result = await self.changes.approve("P1", "ST1", row["review_id"], self.user)
        self.assertEqual(result["status"], "completed")
        self.assertEqual((await self.service.active("P1"))["version_id"], active["version_id"])
        self.usage.execute.assert_not_called()

    async def test_idempotent_submission_and_tampered_review(self):
        payload = self.payload()
        row = await self.submit(payload)
        again = await self.submit(payload)
        self.assertEqual(row["review_id"], again["review_id"])
        self.db["requirement_contexts"].docs[0]["changes"][0]["after"] = "Tampered"
        with self.assertRaises(HTTPException):
            await self.changes.approve("P1", "ST1", row["review_id"], self.user)

    async def test_future_change_cannot_overwrite_newer_knowledge(self):
        row = await self.submit(self.payload(timing="later", target_release="Release 6"))
        await self.changes.approve("P1", "ST1", row["review_id"], self.user)
        draft = await self.service.create_version("P1", "reviewer", KnowledgeDraft(title="Other correction",
            claims=[{**self.claim, "statement": "A different approved correction."}], parent_version_id=self.version["version_id"]))
        latest = await self.service.approve("P1", "reviewer", draft["version_id"])
        with self.assertRaises(HTTPException) as error:
            await self.changes.approve("P1", "ST1", row["review_id"], self.user, activate=True)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual((await self.service.active("P1"))["version_id"], latest["version_id"])

    async def test_missing_blockers_wrong_rule_and_disabled_gate_reject(self):
        payload = self.payload().model_dump()
        payload["decisions"][0]["rule_id"] = "NOT_LINKED"
        with self.assertRaises(HTTPException) as error:
            await self.submit(StoryKnowledgeReviewInput.model_validate(payload))
        self.assertEqual(error.exception.status_code, 422)
        # A separate unresolved blocker may not be hidden by approving the conflict.
        self.db["story_analyses"].docs[0]["findings"].append({"finding_id": "F2", "category": "missing_detail",
            "severity": "blocker", "description": "Missing role", "question": "Which role?"})
        with self.assertRaises(HTTPException) as error:
            await self.submit()
        self.assertEqual(error.exception.status_code, 422)
        fixtures.settings.features.story_analysis = False
        self.assertEqual((await self.client.get(self.path)).status_code, 403)
