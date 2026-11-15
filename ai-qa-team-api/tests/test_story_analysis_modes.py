"""M3 service/ASGI regression with synthetic auth, database and metered AI doubles."""
import unittest

from fastapi import HTTPException
import test_product_knowledge as fixtures
from app.models.product_knowledge import ReviewStoryAnalysis


class StoryAnalysisModes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await fixtures.KnowledgeTests.asyncSetUp(self)

    approved = fixtures.KnowledgeTests.approved
    analysis = fixtures.KnowledgeTests.analysis

    async def test_story_only_without_criteria_review_cannot_enable_generation(self):
        self.db["stories"].docs[0]["acceptance_criteria"] = None
        result = await self.analysis()
        self.assertEqual(result["analysis_mode"], "story_only")
        self.assertIsNone(result["knowledge_version_id"])
        self.assertFalse((await self.service.latest_analysis("P1", "ST1"))["stale"])
        await self.service.review_analysis("P1", "reviewer", "ST1", result["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        self.assertEqual((await self.service.analysis_summaries("P1", ["ST1"]))["ST1"]["state"], "reviewed")
        with self.assertRaises(HTTPException) as failure:
            await self.service.generation_context("P1", "ST1")
        self.assertEqual(failure.exception.status_code, 409)
        self.assertEqual(self.usage.execute.call_args.args[3].max_retries, 0)

    async def test_story_only_with_criteria_is_not_trusted_generation(self):
        result = await self.analysis()
        await self.service.review_analysis("P1", "reviewer", "ST1", result["analysis_id"], ReviewStoryAnalysis(resolutions=[]))
        with self.assertRaises(HTTPException):
            await self.service.generation_context("P1", "ST1")
        await self.approved()
        self.assertTrue((await self.service.latest_analysis("P1", "ST1"))["stale"])
        self.assertEqual((await self.service.analysis_summaries("P1", ["ST1"]))["ST1"]["state"], "stale")
        with self.assertRaises(HTTPException):
            await self.service.review_analysis("P1", "reviewer", "ST1", result["analysis_id"], ReviewStoryAnalysis(resolutions=[]))

    async def test_knowledge_aware_without_criteria_and_legacy_compatibility(self):
        await self.approved()
        self.db["stories"].docs[0]["acceptance_criteria"] = ""
        result = await self.analysis()
        self.assertEqual(result["analysis_mode"], "knowledge_aware")
        self.db["story_analyses"].docs[0].pop("analysis_mode")
        self.assertFalse((await self.service.latest_analysis("P1", "ST1"))["stale"])
        self.db["stories"].docs[0]["description"] = "New requirement"
        self.assertTrue((await self.service.latest_analysis("P1", "ST1"))["stale"])

    async def test_story_only_rejects_invented_knowledge_and_criteria(self):
        finding = {"finding_id": "F1", "category": "knowledge_conflict", "severity": "blocker",
                   "description": "Unsupported", "question": "Clarify?"}
        with self.assertRaises(HTTPException) as failure:
            await self.analysis([finding])
        self.assertEqual(failure.exception.status_code, 502)
        finding.update(category="ambiguity", knowledge_claim_id="K_missing")
        with self.assertRaises(HTTPException):
            await self.analysis([finding])
        finding.update(knowledge_claim_id=None, criterion_quote="Invented criterion")
        with self.assertRaises(HTTPException):
            await self.analysis([finding])
        self.assertEqual(self.db["story_analyses"].docs, [])

    async def test_blank_story_rejected_before_metered_call_and_member_review_guard(self):
        self.db["stories"].docs[0].update(description=" ", acceptance_criteria=None)
        response = await self.client.post(self.base + "/stories/ST1/analyze")
        self.assertEqual(response.status_code, 409)
        self.usage.execute.assert_not_called()
        self.db["stories"].docs[0]["description"] = "Users save a draft for later editing."
        result = await self.analysis()
        self.user["role"] = "MEMBER"
        response = await self.client.post(self.base + f'/stories/ST1/analysis/{result["analysis_id"]}/review', json={"resolutions": []})
        self.assertEqual(response.status_code, 403)
