from fastapi import HTTPException

from app.models.test_design import ScenarioIntents, DesignedTestCases
from app.services.ai.ai_usage_policy import AIOperation
from app.services.product_knowledge import ProductKnowledge
from app.utils.feature_flags import require_features


class KnowledgeTestDesign:
    def __init__(self, database, usage=None):
        self.knowledge = ProductKnowledge(database, usage)

    @staticmethod
    def references(item, story, knowledge):
        criteria = story.get("acceptance_criteria") or ""
        rules = {claim["claim_id"] for claim in knowledge["claims"] if claim["epistemic_status"] == "expected"}
        if any(not quote.strip() or quote not in criteria for quote in item.acceptance_criteria_refs):
            raise HTTPException(502, "Generated coverage must cite exact acceptance criteria.")
        if set(item.rule_references) - rules:
            raise HTTPException(502, "Generated expectations cited an unavailable approved rule.")

    async def scenarios(self, project, user, story, count, complexity):
        require_features("product_knowledge", "story_analysis", "scenario_generation")
        story = await self.knowledge.story(project, story["story_id"])
        context = await self.knowledge.generation_context(project, story["story_id"])
        result = await self.knowledge.ai(AIOperation.SCENARIO_DESIGN, project, user,
            {"story": story, "approved_context": context, "requested_count": count, "complexity": complexity}, ScenarioIntents,
            "scenario_design_v1")
        items = result.scenarios[:count]
        if len({item.title.strip().lower() for item in items}) != len(items):
            raise HTTPException(502, "AI returned duplicate scenario intents. No scenarios were saved.")
        for item in items:
            self.references(item, story, context["knowledge"])
        return [item.model_dump() for item in items], context

    async def testcases(self, project, user, scenario, count):
        require_features("product_knowledge", "story_analysis", "test_generation")
        context = await self.knowledge.generation_context(project, scenario["story_id"])
        if (scenario.get("knowledge_version_id") != context["knowledge"]["version_id"]
                or scenario.get("story_analysis_id") != context["analysis"]["analysis_id"]):
            raise HTTPException(409, "Scenario knowledge or analysis changed. Review a successor scenario before test design.")
        story = await self.knowledge.story(project, scenario["story_id"])
        result = await self.knowledge.ai(AIOperation.TEST_DESIGN, project, user,
            {"story": story, "scenario": {key: scenario.get(key) for key in (
                "scenario_id", "title", "description", "purpose", "role", "coverage_type", "preconditions",
                "expected_outcome", "acceptance_criteria_refs", "rule_references")},
             "approved_context": context, "requested_count": count}, DesignedTestCases,
            "test_design_v1")
        items = result.testcases[:count]
        if len({item.title.strip().lower() for item in items}) != len(items):
            raise HTTPException(502, "AI returned duplicate test cases. No drafts were saved.")
        for item in items:
            self.references(item, story, context["knowledge"])
        return [{**item.model_dump(), "public_data": {entry.name: entry.value for entry in item.public_data}} for item in items], context
