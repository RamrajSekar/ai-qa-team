"""Feature policy regression tests; no live Mongo, Redis, or AI access."""
import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_ENV = {
    "MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "feature_tests",
    "REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_USERNAME": "test",
    "REDIS_PASSWORD": "test-only", "SESSION_SECRET_KEY": "session-test-only",
    "JWT_SECRET_KEY": "jwt-test-only", "OPENAI_API_KEY": "", "FEATURES": "{}",
}
# Override all feature env values, even if a developer enables them locally.
OFF = ["approved_visual_run_admission", "approved_visual_run_execution", "story_management", "scenario_generation", "test_generation", "recorder",
       "native_execution", "jira_trigger", "failure_diagnostics", "self_healing",
       "playwright_repo_adapter", "selenium_repo_adapter"]
ON = ["repository_discovery", "test_registry", "test_data_generation"]
EXPECTED = {**dict.fromkeys(OFF, False), **dict.fromkeys(ON, True)}
TEST_ENV.update({f"FEATURES__{key.upper()}": str(value) for key, value in EXPECTED.items()})

mongo_client = MagicMock()
db = mongo_client.__getitem__.return_value
redis_client = MagicMock()
worker_redis = MagicMock()
worker_redis.brpop = AsyncMock()

with patch.dict(os.environ, TEST_ENV), \
     patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=mongo_client) as mongo_factory, \
     patch("redis.Redis", return_value=redis_client) as redis_factory, \
     patch("redis.asyncio.Redis", return_value=worker_redis), \
     patch("openai.AsyncOpenAI", side_effect=AssertionError("Import-time AI initialization")) as ai_factory:
    from app.config import FeatureFlags, Settings, settings
    from app.main import app
    from app.workers import execution_worker
    from app.services import execution_engine
    from app.routes import scenario_routes, testcase_routes, integration_routes
    from app.utils import execution_queue
    from app.utils.feature_flags import require_features
    from app.utils.jwt_handler import create_access_token
    from app.models.subscription import Subscription

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError


class FeatureFlagTests(unittest.TestCase):
    def setUp(self):
        settings.features = FeatureFlags()
        self.collections = {}
        db.reset_mock()
        redis_client.reset_mock()
        worker_redis.reset_mock()
        def collection(name):
            if name not in self.collections:
                coll = MagicMock(name=name)
                for method in ["find_one", "insert_one", "update_one", "delete_one",
                               "delete_many", "update_many", "find_one_and_update", "count_documents"]:
                    setattr(coll, method, AsyncMock(name=f"{name}.{method}"))
                coll.find_one.return_value = None
                self.collections[name] = coll
            return self.collections[name]
        db.__getitem__.side_effect = collection
        self.client = TestClient(app)  # Deliberately do not run the DB startup lifespan.
        self.addCleanup(self.client.close)
        self.addCleanup(setattr, settings, "features", FeatureFlags())

    def assert_no_external_calls(self):
        self.assertEqual(db.mock_calls, [])
        self.assertEqual(redis_client.mock_calls, [])
        self.assertEqual(worker_redis.mock_calls, [])

    def authenticate(self):
        self.email = "tester@example.com"
        subscription = Subscription()
        subscription.apply_plan_defaults()
        self.user = {"_id": ObjectId(), "email": self.email, "role": "user",
                     "subscription": subscription.model_dump()}
        db["users"].find_one.return_value = self.user
        self.client.headers["Authorization"] = "Bearer " + create_access_token({"email": self.email})

    def test_defaults_and_environment_overrides_preserve_core_settings(self):
        with patch.dict(os.environ, TEST_ENV):
            baseline = Settings(_env_file=None)
            with patch.dict(os.environ, {"FEATURES__STORY_MANAGEMENT": "true",
                                          "FEATURES__TEST_REGISTRY": "false"}):
                changed = Settings(_env_file=None)
        self.assertEqual(baseline.features.model_dump(), EXPECTED)
        self.assertTrue(changed.features.story_management)
        self.assertFalse(changed.features.test_registry)
        self.assertEqual(baseline.model_dump(exclude={"features"}), changed.model_dump(exclude={"features"}))
        self.assertIsNone(settings.openai_api_key or None)
        ai_factory.assert_not_called()
        self.assertEqual(mongo_factory.call_args.args, (TEST_ENV["MONGO_URI"],))
        self.assertEqual(redis_factory.call_args.kwargs["host"], TEST_ENV["REDIS_HOST"])
        self.assertEqual(redis_factory.call_args.kwargs["password"], TEST_ENV["REDIS_PASSWORD"])
        with patch.dict(os.environ, {**TEST_ENV, "FEATURES__RECORDER": "not-a-boolean"}):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)

    def test_features_is_boolean_only_read_only_policy_not_capability_routes(self):
        response = self.client.get("/features")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), EXPECTED)
        self.assertTrue(all(type(value) is bool for value in response.json().values()))
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.client.post("/features", json={"recorder": True}).status_code, 405)
        self.assert_no_external_calls()
        paths = app.openapi()["paths"]
        self.assertNotIn("/stories/", paths)
        self.assertNotIn("/scenarios/", paths)
        self.assertNotIn("/recorder/", paths)
        self.assertNotIn("/testcases/generate", paths)
        self.assertNotIn("/execute/batch", paths)
        self.assertIn("/execute/", paths)
        for absent in ["/registry", "/test-data", "/discovery"]:
            self.assertEqual(self.client.get(absent).status_code, 404)

    def test_all_disabled_http_routes_stop_before_db_ai_queue_or_usage(self):
        cases = []
        for route in app.routes:
            path = getattr(route, "path", "")
            if path.startswith(("/stories", "/scenarios", "/recorder")) or path in {
                "/testcases/generate", "/execute/testcase/{testcase_id}",
                "/execute/batch", "/integrations/{provider}/import",
            }:
                import re
                url = re.sub(r"\{[^}]+\}", "test", path)
                for method in route.methods:
                    cases.append((method, url))
        self.assertGreater(len(cases), 20)
        with ExitStack() as stack:
            ai = stack.enter_context(patch.object(scenario_routes, "generate_scenarios_from_prompt", new_callable=AsyncMock))
            generator = stack.enter_context(patch.object(testcase_routes, "generate_playwright_test"))
            usage = [stack.enter_context(patch.object(module, "increment_usage", new_callable=AsyncMock))
                     for module in (scenario_routes, testcase_routes, execution_engine, execution_worker)]
            for method, url in cases:
                with self.subTest(method=method, url=url):
                    response = self.client.request(method, url, json={})
                    self.assertEqual(response.status_code, 403, response.text)
                    self.assertEqual(response.json()["detail"]["code"], "feature_disabled")
                    self.assert_no_external_calls()
            ai.assert_not_called()
            generator.assert_not_called()
            for increment in usage:
                increment.assert_not_called()

    def test_import_requires_each_legacy_flag_independently(self):
        names = ["playwright_repo_adapter", "story_management", "scenario_generation", "test_generation"]
        for disabled in names:
            with self.subTest(disabled=disabled):
                settings.features = FeatureFlags(**dict.fromkeys(names, True))
                setattr(settings.features, disabled, False)
                response = self.client.post("/integrations/github/import", json={})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["detail"]["feature"], disabled)
                self.assert_no_external_calls()

    def test_recording_generation_cannot_bypass_disabled_recorder(self):
        settings.features = FeatureFlags(story_management=True, scenario_generation=True)
        response = self.client.post("/scenarios/generate-from-recording", json={})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["feature"], "recorder")
        self.assert_no_external_calls()

    def test_execution_services_and_dormant_enqueue_helper_are_guarded(self):
        args = dict(project_id="P", testcase_id="T", triggered_by="test", env_type="qa",
                    environment_doc={}, runner_type="manual")
        with self.assertRaises(HTTPException):
            asyncio.run(execution_engine.create_execution_record(**args))
        with self.assertRaises(HTTPException):
            asyncio.run(execution_engine.queue_test_execution(
                **args, user_identifier="test", story_id=None, scenario_id=None,
                credentials=None, role=None, browser=None, headed=False, dataset=None))
        with self.assertRaises(HTTPException):
            execution_queue.enqueue_execution_job({"execution_id": "EX1"})
        self.assert_no_external_calls()

    def test_disabled_worker_does_not_dequeue_or_run_any_runner(self):
        with patch.object(execution_worker, "execute_playwright_test", new_callable=AsyncMock) as runner, \
             patch.object(execution_worker, "_run_manual", new_callable=AsyncMock) as manual, \
             patch.object(execution_worker, "_run_cloud", new_callable=AsyncMock) as cloud, \
             patch.object(execution_worker, "increment_usage", new_callable=AsyncMock) as usage:
            asyncio.run(execution_worker.worker_loop())
            for operation in (runner, manual, cloud, usage):
                operation.assert_not_called()
            self.assert_no_external_calls()

    def test_enabled_worker_still_reaches_queue(self):
        settings.features.native_execution = True
        worker_redis.brpop.side_effect = asyncio.CancelledError
        try:
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(execution_worker.worker_loop())
            worker_redis.brpop.assert_awaited_once()
        finally:
            worker_redis.brpop.side_effect = None

    def test_execution_history_and_ownership_still_work(self):
        self.authenticate()
        doc = {"_id": ObjectId(), "execution_id": "EX1", "project_id": "P", "testcase_id": "T",
               "status": "passed", "headed": False, "triggered_by": self.email, "runner_type": "manual"}
        executions = db["executions"]
        executions.find_one.side_effect = lambda *a, **kw: copy.deepcopy(doc)
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__aiter__.side_effect = lambda: AsyncRows([copy.deepcopy(doc)])
        executions.find.return_value = cursor
        single = self.client.get("/execute/EX1")
        listing = self.client.get("/execute/")
        direct_listing = self.client.get("/execute?skip=0&limit=200", follow_redirects=False)
        self.assertEqual(direct_listing.status_code, 200, direct_listing.text)
        self.assertNotIn("location", direct_listing.headers)
        self.assertEqual(direct_listing.json(), listing.json())
        self.assertEqual(single.status_code, 200, single.text)
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual(listing.json()[0]["execution_id"], "EX1")
        doc["triggered_by"] = "another@example.com"
        self.assertEqual(self.client.get("/execute/EX1").status_code, 403)
        for coll in self.collections.values():
            coll.insert_one.assert_not_called()
            coll.update_one.assert_not_called()
        self.assertEqual(redis_client.mock_calls, [])

    def test_localhost_ui_history_preflight(self):
        response = self.client.options('/execute?skip=0&limit=200', headers={
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'content-type',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['access-control-allow-origin'], 'http://localhost:3000')
        self.assertEqual(response.headers['access-control-allow-credentials'], 'true')
        denied = self.client.options('/execute', headers={
            'Origin': 'http://untrusted.invalid', 'Access-Control-Request-Method': 'GET',
        })
        self.assertEqual(denied.status_code, 400)
        self.assertNotIn('access-control-allow-origin', denied.headers)

    def test_authentication_and_core_project_environment_subscription_flows(self):
        for url in ["/projects", "/environments", "/auth/check-plan"]:
            self.assertEqual(self.client.get(url).status_code, 401)
        self.authenticate()
        db["counters"].find_one_and_update.return_value = {"seq": 1}
        for name in ["projects", "environments"]:
            db[name].insert_one.return_value = MagicMock(inserted_id=ObjectId())
        project = self.client.post("/projects", json={"name": "Flag test", "created_by": self.email})
        self.assertEqual(project.status_code, 200, project.text)
        db["projects"].find_one.return_value = {"project_id": "PRJ001", "created_by": self.email}
        db["project_memberships"].find_one.return_value = {
            "project_id": "PRJ001", "email": self.email, "role": "ADMIN", "status": "ACTIVE"
        }
        environment = self.client.post("/environments", json={"project_id": "PRJ001", "base_url": "https://example.com"})
        self.assertEqual(environment.status_code, 200, environment.text)
        self.assertEqual(self.client.get("/auth/plans").status_code, 200)
        plan = self.client.get("/auth/check-plan")
        self.assertEqual(plan.status_code, 200, plan.text)
        self.assertEqual(plan.json()["subscription"]["plan"], self.user["subscription"]["plan"])
        db["projects"].insert_one.assert_awaited_once()
        db["environments"].insert_one.assert_awaited_once()
        self.assertTrue(db["users"].update_one.called)  # Existing onboarding/usage behavior retained.

    def test_enabled_story_route_is_restored(self):
        settings.features.story_management = True
        self.authenticate()
        cursor = MagicMock()
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=[])
        db["stories"].find.return_value = cursor
        response = self.client.get("/stories/?project_id=P")
        self.assertEqual(response.status_code, 200, response.text)
        db["stories"].find.assert_called_once()

    def test_dormant_generator_is_guarded_if_registered(self):
        path = Path(__file__).resolve().parents[1] / "app/routes/generate-tests.py"
        spec = importlib.util.spec_from_file_location("dormant_generator", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        isolated = FastAPI()
        isolated.include_router(module.router)
        with TestClient(isolated) as client:
            response = client.post("/generate-tests/generate-tests?scenario_id=unused")
        self.assertEqual(response.status_code, 403)
        self.assert_no_external_calls()

    def test_unknown_flag_is_a_configuration_error(self):
        with self.assertRaises(ValueError):
            require_features("typo")


class AsyncRows:
    def __init__(self, rows):
        self.rows = iter(rows)
    def __aiter__(self):
        return self
    async def __anext__(self):
        try:
            return next(self.rows)
        except StopIteration:
            raise StopAsyncIteration


if __name__ == "__main__":
    unittest.main()
