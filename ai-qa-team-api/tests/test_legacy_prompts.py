"""Legacy prompt migration: synthetic contracts, auth and provider doubles only."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "prompt_tests",
                            "REDIS_HOST": "localhost", "REDIS_PORT": "6399", "REDIS_USERNAME": "", "REDIS_PASSWORD": "",
                            "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app.ai.scenario_prompts import build_scenario_prompt_from_story, build_scenario_prompt_from_recording
    from app.ai.prompts import generate_testcase_prompt
    from app.services import prompt_registry_service as registry
    from app.services.ai import scenario_generator
    from app.services.prompt_templates import render_template
    from app.routes import platform_admin_routes
    from app.utils.auth_dependency import get_current_user
    from test_platform_admin_prompts import DB


class LegacyPromptTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = DB()
        self.patcher = patch.object(registry, "db", self.db)
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        self.story = {"project_id": "P1", "story_id": "ST1", "title": "Save draft", "description": "Save synthetic values."}
        self.recording = {"recording_id": "R1", "title": "Synthetic recording", "description": "Sample only",
                          "raw_events": [{"action": "click"}], "high_level_steps": ["Save draft"]}

    async def test_code_defaults_preserve_all_legacy_contracts(self):
        expected = json.loads((Path(__file__).parent / "fixtures/legacy_prompt_contracts.json").read_text(encoding="utf-8"))
        for level in ("basic", "medium", "advanced"):
            self.assertEqual(build_scenario_prompt_from_story("Scenario Builder", self.story, 3, level), expected["story_" + level])
            self.assertEqual(build_scenario_prompt_from_recording("Scenario Builder", self.story, self.recording, 3, level), expected["recording_" + level])
        self.assertEqual(generate_testcase_prompt(self.story), expected["testcase"])
        self.assertEqual(self.db["prompt_definitions"].documents, [])

    async def test_draft_activation_and_rollback_with_separate_customer_context(self):
        for key in ("LEGACY_STORY_SCENARIOS", "LEGACY_RECORDING_SCENARIOS", "LEGACY_TESTCASE"):
            definition = await registry.get_prompt_definition(key)
            self.assertTrue(definition["template_variables"])
            draft = await registry.create_draft(key, "owner@example.test")
            await registry.update_draft(key, 1, draft["system_prompt"] + "\nPreserve terminology.")
            self.assertEqual((await registry.get_active(key))["source"], "CODE_FALLBACK")
            await registry.activate_version(key, 1)
            self.assertEqual((await registry.get_active(key))["resolved_version"], 1)
            await registry.create_draft(key, "owner@example.test")
            await registry.activate_version(key, 2)
            await registry.activate_version(key, 1)
            with self.assertRaises(HTTPException): await registry.update_draft(key, 1, draft["system_prompt"])
        self.assertNotIn(self.story["description"], str(self.db["prompt_definitions"].documents))

    async def test_slots_are_allowlisted_and_values_are_not_rerendered(self):
        self.assertEqual(render_template("Title: {{title}}; count={{count}}", {"title": "{{count}}", "count": 3}), "Title: {{count}}; count=3")
        draft = await registry.create_draft("LEGACY_STORY_SCENARIOS", "owner@example.test")
        for text in (draft["system_prompt"].replace("{{title}}", "{{__class__}}"), draft["system_prompt"].replace("{{count}}", "")):
            with self.assertRaises(HTTPException) as error: await registry.update_draft("LEGACY_STORY_SCENARIOS", 1, text)
            self.assertEqual(error.exception.status_code, 422)

    async def test_provider_receives_prompt_identity_without_registry_writes(self):
        gateway = SimpleNamespace(generate=AsyncMock(return_value=SimpleNamespace(text='[{"title":"Synthetic","steps":[]}]')))
        with patch.object(scenario_generator, "LLMGateway", return_value=gateway):
            result = await scenario_generator.generate_scenarios_from_prompt("P1", "Synthetic context", prompt_key="LEGACY_STORY_SCENARIOS", prompt_version="2")
        self.assertEqual(result[0]["title"], "Synthetic")
        request = gateway.generate.call_args.args[1]
        self.assertEqual((request.prompt_key, request.prompt_version), ("LEGACY_STORY_SCENARIOS", "2"))
        self.assertIn("untrusted", request.system_prompt)

    async def test_project_admin_denied_every_registry_operation(self):
        app = FastAPI(); app.include_router(platform_admin_routes.router)
        app.dependency_overrides[get_current_user] = lambda: {"email": "project-admin@example.test", "role": "admin", "platform_role": "NONE"}
        client = TestClient(app)
        for method, path, body in (("GET", "", None), ("GET", "/LEGACY_STORY_SCENARIOS", None),
                                  ("GET", "/LEGACY_STORY_SCENARIOS/versions", None),
                                  ("POST", "/LEGACY_STORY_SCENARIOS/versions", {}),
                                  ("PATCH", "/LEGACY_STORY_SCENARIOS/versions/1", {"system_prompt": "A valid synthetic prompt."}),
                                  ("POST", "/LEGACY_STORY_SCENARIOS/versions/1/activate", {})):
            response = client.request(method, "/platform-admin/prompts" + path, **({"json": body} if body is not None else {}))
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db["prompt_definitions"].documents, [])

    async def test_validation_does_not_echo_prompt_content(self):
        app = FastAPI(); app.include_router(platform_admin_routes.router)
        app.dependency_overrides[get_current_user] = lambda: {"email": "owner@example.test", "platform_role": "OWNER"}
        response = TestClient(app).patch("/platform-admin/prompts/BUG_INTERPRETER/versions/1", json={"system_prompt": "CANARY"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("CANARY", response.text)


if __name__ == "__main__": unittest.main()
