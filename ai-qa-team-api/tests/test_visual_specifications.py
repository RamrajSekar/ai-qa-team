"""Authoring/compilation checks with synthetic auth and in-memory Mongo doubles."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI, HTTPException

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "spec_tests",
                            "REDIS_HOST": "localhost", "REDIS_PORT": "6399", "REDIS_USERNAME": "",
                            "REDIS_PASSWORD": "", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from app.config import FeatureFlags, settings
    from app.routes import visual_specification_routes as routes
    from test_approved_visual_runs import CollectionDouble


class Cursor:
    def __init__(self, docs): self.docs = docs
    def sort(self, field, order):
        self.docs.sort(key=lambda item: item[field], reverse=order == -1)
        return self
    async def to_list(self, limit): return deepcopy(self.docs[:limit])


class Collection(CollectionDouble):
    def find(self, query):
        return Cursor([deepcopy(doc) for doc in self.docs if self.matches(doc, query)])


class VisualSpecificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = {name: Collection() for name in ("visual_workflow_versions", "visual_test_spec_versions")}
        self.db.update({
            "testcases": Collection({"project_id": "P1", "testcase_id": "TC1", "scenario_id": "SC1"}),
            "scenarios": Collection({"project_id": "P1", "scenario_id": "SC1", "story_id": "ST1", "approved": True}),
            "stories": Collection({"project_id": "P1", "story_id": "ST1", "acceptance_criteria": "Display the expected text."}),
            "environments": Collection({"project_id": "P1", "env_id": "ENV1", "revision": 1,
                                        "base_url": "https://test.salesforce.com", "credentials": []}),
        })
        self.user = {"_id": "reviewer", "role": "ADMIN"}
        async def member(project, user):
            if project != "P1": raise HTTPException(404, "Access denied")
        async def admin(project, user):
            await member(project, user)
            if user["role"] != "ADMIN": raise HTTPException(403, "Admin required")
        for target, name, value in ((routes, "db", self.db), (routes, "require_project_member", member),
                                    (routes, "require_project_admin", admin),
                                    (settings, "features", FeatureFlags(reusable_workflows=True)),
                                    (settings, "app_env", "test")):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user] = lambda: self.user
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.base = "/projects/P1/visual-specifications"

    async def workflow(self, steps, **fields):
        response = await self.client.post(self.base + "/workflows", json={"title": "Setup", "steps": steps, **fields})
        self.assertEqual(response.status_code, 201, response.text)
        version = response.json()
        approved = await self.client.post(self.base + "/workflows/" + version["version_id"] + "/approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        return approved.json()

    async def specification(self, steps):
        response = await self.client.post(self.base + "/cases/TC1", json={"steps": steps})
        self.assertEqual(response.status_code, 201, response.text)
        version = response.json()
        approved = await self.client.post(self.base + "/cases/TC1/" + version["version_id"] + "/approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        return approved.json()

    async def preview(self, version, **selection):
        return await self.client.post(self.base + "/cases/TC1/" + version["version_id"] + "/preview",
                                      json={"environment_id": "ENV1", **selection})

    async def test_public_case_needs_no_login_or_reusable_workflow(self):
        version = await self.specification([{"action": "click", "target": "Help"}, {"action": "assert_text", "expected": "Help center"}])
        response = await self.preview(version)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(version["acceptance_criteria_snapshot"], "Display the expected text.")
        self.assertFalse(result["requires_credentials"])
        self.assertFalse(result["execution_ready"])
        self.assertIsNone(result.get("application_role"))
        from app.services.approved_visual_run import digest
        unsigned = {key: value for key, value in result.items() if key != "manifest_digest"}
        self.assertEqual(result["manifest_digest"], digest(unsigned, settings.jwt_secret_key.encode()))
        self.assertEqual(result["workflow_versions"], [])
        self.assertEqual(result["approved_specification_version_id"], version["version_id"])
        self.assertEqual([step["action"] for step in result["steps"]], ["click", "assert_text"])
        self.assertEqual((await self.preview(version, application_role="qa")).status_code, 422)

    async def test_immutable_run_admission_is_idempotent_scoped_and_never_launches(self):
        self.db["approved_workflow_runs"] = Collection()
        settings.features.approved_visual_run_admission = True
        version = await self.specification([{"action": "click", "target": "Help"}, {"action": "assert_text", "expected": "Help center"}])
        preview = (await self.preview(version)).json()
        path = self.base + "/cases/TC1/" + version["version_id"] + "/runs"
        payload = {"environment_id": "ENV1", "preview_digest": preview["manifest_digest"], "idempotency_key": "a" * 32}
        response = await self.client.post(path, json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        run = response.json()
        self.assertFalse(run["execution_ready"])
        self.assertEqual(run["state"], "prepared")
        self.assertEqual(run["manifest"]["environment_revision"], 1)
        self.assertEqual(run["manifest"]["approved_specification_version_id"], version["version_id"])
        original = deepcopy(run["manifest"])
        self.assertEqual((await self.client.post(path, json=payload)).json()["run_id"], run["run_id"])
        self.assertEqual(len(self.db["approved_workflow_runs"].docs), 1)
        bad = {**payload, "environment_id": "FOREIGN"}
        self.assertEqual((await self.client.post(path, json=bad)).status_code, 409)
        self.assertEqual((await self.client.get(f'/projects/P2/visual-specifications/runs/{run["run_id"]}')).status_code, 404)
        self.db["environments"].docs[0]["revision"] = 2
        # New admissions revalidate; the original immutable manifest remains inspectable.
        stale = {**payload, "idempotency_key": "b" * 32}
        self.assertEqual((await self.client.post(path, json=stale)).status_code, 409)
        cancelled = await self.client.post(self.base + f'/runs/{run["run_id"]}/cancel')
        self.assertEqual(cancelled.json()["state"], "cancelled")
        self.assertEqual(cancelled.json()["manifest"], original)
        settings.features.approved_visual_run_admission = False
        self.assertEqual((await self.client.get(self.base + f'/runs/{run["run_id"]}')).status_code, 403)

    async def test_reusable_versions_compile_parameters_and_credential_references(self):
        workflow = await self.workflow([
            {"action": "type", "target": "Username", "value": {"source": "credential", "field": "username"}},
            {"action": "type", "target": "Password", "value": {"source": "credential", "field": "password"}},
            {"action": "type", "target": "Alias", "value": {"source": "parameter", "name": "alias"}},
            {"action": "assert_text", "expected": "Dashboard"},
        ])
        version = await self.specification([{"action": "reusable", "workflow_version_id": workflow["version_id"],
                                             "inputs": {"alias": {"source": "literal", "text": "Synthetic"}}}])
        self.assertEqual((await self.preview(version)).status_code, 409)
        self.db["environments"].docs[0].update({"secret_payload": {"ciphertext": "cipher-canary"},
            "credentials": [{"role": "qa", "credential_id": "c" * 32, "username": "username-canary", "password_configured": True}]})
        response = await self.preview(version, application_role="qa")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["workflow_versions"][0]["version_id"], workflow["version_id"])
        self.assertEqual(response.json()["steps"][2]["value"], {"source": "literal", "text": "Synthetic"})
        self.assertEqual(response.json()["steps"][1]["value"], {"source": "credential", "field": "password"})
        self.assertNotIn("username-canary", response.text)
        self.assertNotIn("cipher-canary", response.text)

    async def test_workflow_successor_flags_dependent_case_without_mutating_approval(self):
        workflow = await self.workflow([{"action": "assert_text", "expected": "Before"}])
        version = await self.specification([{"action": "reusable", "workflow_version_id": workflow["version_id"]}])
        original = deepcopy(self.db["visual_test_spec_versions"].docs[0])
        await self.workflow([{"action": "assert_text", "expected": "After"}], workflow_id=workflow["workflow_id"])
        state = (await self.client.get(self.base + "/cases/TC1")).json()
        self.assertTrue(state["review_required"])
        self.assertEqual((await self.preview(version)).status_code, 409)
        self.assertEqual(self.db["visual_test_spec_versions"].docs[0], original)

    async def test_expected_results_required_and_source_edits_require_review(self):
        draft = (await self.client.post(self.base + "/cases/TC1", json={"steps": [{"action": "click", "target": "Help"}]})).json()
        self.assertEqual((await self.client.post(self.base + "/cases/TC1/" + draft["version_id"] + "/approve")).status_code, 409)
        version = await self.specification([{"action": "assert_text", "expected": "Help"}])
        self.db["stories"].docs[0]["acceptance_criteria"] = "Changed expectation"
        self.assertEqual((await self.preview(version)).status_code, 409)
        self.assertTrue((await self.client.get(self.base + "/cases/TC1")).json()["review_required"])

    async def test_unapproved_versions_and_unbound_parameters_reject(self):
        steps = [{"action": "type", "target": "Alias", "value": {"source": "parameter", "name": "alias"}},
                 {"action": "assert_text", "expected": "Ready"}]
        draft = (await self.client.post(self.base + "/workflows", json={"title": "Parameterized", "steps": steps})).json()
        call = {"action": "reusable", "workflow_version_id": draft["version_id"]}
        self.assertEqual((await self.client.post(self.base + "/cases/TC1", json={"steps": [call]})).status_code, 409)
        await self.client.post(self.base + "/workflows/" + draft["version_id"] + "/approve")
        self.assertEqual((await self.client.post(self.base + "/cases/TC1", json={"steps": [call]})).status_code, 422)
        self.assertEqual((await self.client.post(self.base + "/cases/TC1", json={"steps": steps})).status_code, 422)
        call["inputs"] = {"wrong": {"source": "literal", "text": "Synthetic"}}
        self.assertEqual((await self.client.post(self.base + "/cases/TC1", json={"steps": [call]})).status_code, 422)
        self.assertEqual(self.db["visual_test_spec_versions"].docs, [])

    async def test_draft_successors_and_repeated_approval_preserve_active_version(self):
        workflow = await self.workflow([{"action": "assert_text", "expected": "Ready"}])
        version = await self.specification([{"action": "reusable", "workflow_version_id": workflow["version_id"]}])
        draft = await self.client.post(self.base + "/workflows", json={"workflow_id": workflow["workflow_id"], "title": "New draft", "steps": [{"action": "click", "target": "Help"}]})
        self.assertEqual(draft.status_code, 201)
        self.assertEqual((await self.preview(version)).status_code, 200)
        repeat = await self.client.post(self.base + "/workflows/" + workflow["version_id"] + "/approve")
        self.assertEqual(repeat.json(), workflow)
        missing_assertion = await self.client.post(self.base + "/workflows/" + draft.json()["version_id"] + "/approve")
        self.assertEqual(missing_assertion.status_code, 409)

    async def test_gates_authorization_unsupported_actions_and_validation_redaction(self):
        self.assertEqual((await self.client.get(self.base.replace("P1", "P2") + "/workflows")).status_code, 404)
        workflow = await self.workflow([{"action": "assert_text", "expected": "Ready"}])
        self.user["role"] = "TESTER"
        draft = (await self.client.post(self.base + "/workflows", json={"title": "Draft", "steps": workflow["steps"]})).json()
        self.assertEqual((await self.client.post(self.base + "/workflows/" + draft["version_id"] + "/approve")).status_code, 403)
        response = await self.client.post(self.base + "/workflows", json={"title": "Unsafe", "steps": [{"action": "javascript", "code": "secret-canary"}]})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("secret-canary", response.text)
        for path in ("//other.test", "/../outside", "/%2e%2e/outside", "/?token=secret-canary"):
            self.assertEqual((await self.client.post(self.base + "/workflows", json={"title": "Bad path", "steps": [{"action": "navigate", "path": path}]})).status_code, 422)
        settings.features.reusable_workflows = False
        self.assertEqual((await self.client.get(self.base + "/workflows")).status_code, 403)
        settings.features.reusable_workflows = True
        settings.app_env = "production"
        self.assertEqual((await self.client.get(self.base + "/workflows")).status_code, 403)

    async def test_nested_unapproved_foreign_and_oversized_workflow_calls_reject(self):
        workflow = await self.workflow([{"action": "click", "target": "Help"}, {"action": "assert_text", "expected": "Help"}])
        call = {"action": "reusable", "workflow_version_id": workflow["version_id"]}
        self.assertEqual((await self.client.post(self.base + "/workflows", json={"title": "Nested", "steps": [call]})).status_code, 422)
        self.assertEqual((await self.client.post(self.base + "/cases/TC1", json={"steps": [call] * 21})).status_code, 422)
        foreign = deepcopy(self.db["visual_workflow_versions"].docs[0])
        foreign.update({"_id": "f" * 32, "version_id": "f" * 32, "project_id": "P2"})
        self.db["visual_workflow_versions"].docs.append(foreign)
        self.assertEqual((await self.client.post(self.base + "/cases/TC1", json={"steps": [{"action": "reusable", "workflow_version_id": "f" * 32}]})).status_code, 404)
        self.assertEqual(self.db["visual_test_spec_versions"].docs, [])
