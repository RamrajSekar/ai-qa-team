"""Count accounting tests with database, authorization and AI doubles."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "count_tests", "REDIS_HOST": "localhost",
                            "REDIS_PORT": "6399", "REDIS_USERNAME": "", "REDIS_PASSWORD": "", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from app.routes import scenario_routes as routes
    from app.config import FeatureFlags, settings


class ScenarioCountTests(unittest.IsolatedAsyncioTestCase):
    async def run_generation(self, scenario_limit, ai_limit, requested, actual, knowledge=False):
        story = {"story_id": "ST1", "project_id": "P1", "title": "Save", "acceptance_criteria": "Draft saved"}
        stories = SimpleNamespace(find_one=AsyncMock(return_value=story))
        scenarios = SimpleNamespace(count_documents=AsyncMock(return_value=0), insert_one=AsyncMock(return_value=SimpleNamespace(inserted_id="row")))
        db = {"stories": stories, "scenarios": scenarios, "projects": SimpleNamespace(find_one=AsyncMock(return_value={}))}
        sub = {"plan": "free", "limits": {"scenarios_limit": scenario_limit, "ai_gen_limit": ai_limit}, "usage": {"ai_gen_used": 0}}
        rows = [{"title": f"Intent {i}", "steps": []} for i in range(actual)]
        designer = MagicMock(); designer.scenarios = AsyncMock(return_value=(rows, {"knowledge": {"version_id": "k"}, "analysis": {"analysis_id": "a"}}))
        with patch.object(routes, "db", db), patch.object(settings, "features", FeatureFlags(product_knowledge=knowledge)), \
             patch.object(routes, "get_subscription", AsyncMock(return_value=sub)), \
             patch.object(routes, "require_project_member", AsyncMock()), \
             patch.object(routes, "get_next_sequence", AsyncMock(side_effect=[f"SC{i}" for i in range(actual)])), \
             patch.object(routes, "increment_usage", AsyncMock()) as increments, \
             patch.object(routes, "generate_scenarios_from_prompt", AsyncMock(return_value=rows)) as generator, \
             patch.object(routes, "KnowledgeTestDesign", return_value=designer):
            result = await routes.generate_scenarios_from_story(story_id="ST1", count=requested, complexity="basic", current_user={"email": "dev@example.test"})
            return result, increments.await_count, generator.await_count, designer.scenarios.await_count

    async def test_legacy_partial_generation_reports_actual_and_spends_actual(self):
        result, increments, calls, _ = await self.run_generation(10, 10, 3, 1)
        self.assertEqual((result.summary.requested_count, result.summary.allowed_count, result.summary.generated_count), (3, 3, 1))
        self.assertEqual((result.summary.remaining_ai_generations, result.summary.remaining_scenario_slots), (9, 9))
        self.assertEqual((increments, calls), (2, 1))

    async def test_knowledge_batch_charge_is_not_duplicated_per_row(self):
        result, increments, calls, design = await self.run_generation(2, 10, 3, 2, True)
        self.assertEqual((result.summary.allowed_count, result.summary.generated_count), (2, 2))
        self.assertEqual((increments, calls, design), (2, 0, 1))
        self.assertEqual(result.summary.remaining_ai_generations, 9)

    async def test_exhausted_allowance_does_not_invoke_ai(self):
        result, increments, calls, design = await self.run_generation(0, 10, 3, 0)
        self.assertEqual(result.summary.generated_count, 0)
        self.assertEqual((increments, calls, design), (0, 0, 0))

    async def test_unlimited_legacy_allowances_are_supported(self):
        result, _, _, _ = await self.run_generation(None, None, 3, 2)
        self.assertEqual(result.summary.generated_count, 2)
        self.assertIsNone(result.summary.remaining_ai_generations)
        self.assertIsNone(result.summary.remaining_scenario_slots)
