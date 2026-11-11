import os
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "platform_tests", "REDIS_HOST": "localhost", "REDIS_PORT": "6379",
    "REDIS_USERNAME": "test", "REDIS_PASSWORD": "test", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test", "OPENAI_API_KEY": ""}

with patch.dict(os.environ, TEST_ENV):
    from app.config import settings
    from app.models.prompt_registry_model import PromptDraftCreate, PromptDraftUpdate
    from app.models.user_model import User
    from app.routes import auth_routes, platform_admin_routes, user_routes
    from app.services import platform_role_service, prompt_registry_service
    from app.services.prompt_defaults import BUG_INTERPRETER_SYSTEM_PROMPT
    from app.utils.mongo_helper import serialize_public_user
    from app.utils.platform_authorization import require_platform_admin, require_platform_owner


class Result:
    def __init__(self, modified_count=0, inserted_id="U1"): self.modified_count = modified_count; self.inserted_id = inserted_id


class Collection:
    def __init__(self): self.documents = []; self.updates = []
    def __bool__(self): raise NotImplementedError("Database collections do not implement truth-value testing")
    async def find_one(self, query): return next((item for item in self.documents if all(item.get(key) == value for key, value in query.items())), None)
    async def insert_one(self, document): self.documents.append(deepcopy(document)); return Result(inserted_id=f"ID{len(self.documents)}")
    async def update_one(self, query, update, upsert=False):
        self.updates.append((deepcopy(query), deepcopy(update)))
        item = await self.find_one(query)
        if not item: return Result()
        for key, value in update.get("$set", {}).items(): item[key] = deepcopy(value)
        for key, value in update.get("$inc", {}).items(): item[key] = item.get(key, 0) + value
        return Result(modified_count=1)


class DB(dict):
    def __missing__(self, key): self[key] = Collection(); return self[key]


class PlatformAdminPromptTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = DB()
        self.patches = [patch.object(prompt_registry_service, "db", self.db), patch.object(platform_role_service, "db", self.db)]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()

    def test_missing_platform_role_serializes_as_none_and_user_default_is_none(self):
        self.assertEqual(serialize_public_user({"email": "user@example.com"})["platform_role"], "NONE")
        self.assertEqual(User(name="User", email="user@example.com").platform_role, "NONE")

    async def test_owner_bootstrap_normalizes_and_persists_without_destructive_sync(self):
        user = {"_id": "U1", "email": " Owner@Example.com ", "platform_role": "NONE"}; self.db["users"].documents.append(user)
        with patch.object(settings, "platform_owner_email", " owner@example.COM "):
            await platform_role_service.ensure_platform_owner(user, trusted_for_bootstrap=True)
        self.assertEqual(user["platform_role"], "OWNER")
        with patch.object(settings, "platform_owner_email", "different@example.com"):
            await platform_role_service.ensure_platform_owner(user, trusted_for_bootstrap=True)
        self.assertEqual(user["platform_role"], "OWNER")

    async def test_nonmatching_and_untrusted_users_remain_none(self):
        with patch.object(settings, "platform_owner_email", "owner@example.com"):
            normal = await platform_role_service.ensure_platform_owner({"email": "user@example.com"}, trusted_for_bootstrap=True)
            untrusted = await platform_role_service.ensure_platform_owner({"email": "owner@example.com"}, trusted_for_bootstrap=False)
        self.assertEqual((normal["platform_role"], untrusted["platform_role"]), ("NONE", "NONE"))

    async def test_platform_authorization_is_independent_from_project_roles(self):
        for role in ("OWNER", "ADMIN"):
            self.assertEqual((await require_platform_admin({"platform_role": role}))["platform_role"], role)
        self.assertEqual((await require_platform_owner({"platform_role": "OWNER"}))["platform_role"], "OWNER")
        for user in ({"platform_role": "NONE", "role": "admin"}, {"platform_role": "NONE", "role": "tester"}, {}):
            with self.assertRaises(HTTPException): await require_platform_admin(user)
        for role in ("ADMIN", "NONE"):
            with self.assertRaises(HTTPException): await require_platform_owner({"platform_role": role})

    def test_unauthenticated_platform_api_is_rejected(self):
        app = FastAPI(); app.include_router(platform_admin_routes.router)
        self.assertEqual(TestClient(app).get("/platform-admin/prompts").status_code, 401)

    async def test_signup_and_profile_payload_cannot_self_promote(self):
        users = self.db["users"]
        with (
            patch.object(auth_routes, "db", self.db), patch.object(auth_routes.pwd_context, "hash", return_value="hash"),
            patch.object(auth_routes, "create_access_token", return_value="access"), patch.object(auth_routes, "create_refresh_token", return_value="refresh"),
            patch.object(auth_routes, "store_refresh_token"), patch.object(settings, "platform_owner_email", "different@example.com"),
        ):
            response = await auth_routes.signup(User(name="User", email="user@example.com", password="password", platform_role="OWNER"))
        self.assertEqual(users.documents[0]["platform_role"], "NONE")
        self.assertEqual(response.body.decode().count('"platform_role":"NONE"'), 1)
        users.updates.clear()
        with patch.object(user_routes, "db", self.db):
            await user_routes.update_onboarding({"step_key": "project", "current_step": 2, "platform_role": "ADMIN"}, {"email": "user@example.com"})
        self.assertNotIn("platform_role", str(users.updates))

    async def test_auth_me_safely_returns_platform_role(self):
        user = {"_id": "U1", "email": "legacy@example.com", "name": "Legacy", "provider": "local"}
        self.db["users"].documents.append(user)
        request = Request({"type": "http", "method": "GET", "path": "/auth/me", "headers": []})
        with (
            patch.object(auth_routes, "db", self.db), patch.object(auth_routes, "extract_token", return_value="token"),
            patch.object(auth_routes, "decode_token", return_value={"email": "legacy@example.com"}),
            patch.object(auth_routes, "sync_usage", new=AsyncMock(return_value={})), patch.object(settings, "platform_owner_email", None),
        ):
            response = await auth_routes.get_my_profile(request)
        self.assertEqual(response["user"]["platform_role"], "NONE")

    async def test_fallback_definition_and_resolution_do_not_persist(self):
        definition = await prompt_registry_service.get_prompt_definition("BUG_INTERPRETER")
        self.assertEqual((definition["output_contract"], definition["active"]["resolved_version"], definition["active"]["source"]), ("TestIntentV1", "CODE_DEFAULT_V1", "CODE_FALLBACK"))
        self.assertEqual(definition["active"]["system_prompt"], BUG_INTERPRETER_SYSTEM_PROMPT)
        await prompt_registry_service.list_prompts(); await prompt_registry_service.list_prompts()
        self.assertEqual(self.db["prompt_definitions"].documents, [])

    async def test_owner_and_admin_prompt_routes_and_normal_users_denied(self):
        for role in ("OWNER", "ADMIN"):
            user = {"email": f"{role.lower()}@example.com", "platform_role": role}
            await require_platform_admin(user)
            result = await platform_admin_routes.get_prompts(user)
            self.assertEqual(result[0]["prompt_key"], "BUG_INTERPRETER")
        for user in ({"platform_role": "NONE", "role": "admin"}, {"platform_role": "NONE", "role": "tester"}, {"platform_role": "NONE"}):
            with self.assertRaises(HTTPException): await require_platform_admin(user)

    async def test_draft_edit_activation_and_rollback_are_atomic(self):
        v1 = await prompt_registry_service.create_draft("BUG_INTERPRETER", "owner@example.com")
        self.assertEqual(v1["system_prompt"], BUG_INTERPRETER_SYSTEM_PROMPT)
        await prompt_registry_service.update_draft("BUG_INTERPRETER", 1, BUG_INTERPRETER_SYSTEM_PROMPT + "\nPreserve field labels.")
        await prompt_registry_service.activate_version("BUG_INTERPRETER", 1)
        v2 = await prompt_registry_service.create_draft("BUG_INTERPRETER", "admin@example.com")
        await prompt_registry_service.update_draft("BUG_INTERPRETER", 2, v2["system_prompt"] + "\nPreserve section headings.")
        await prompt_registry_service.activate_version("BUG_INTERPRETER", 2)
        await prompt_registry_service.activate_version("BUG_INTERPRETER", 1)
        document = self.db["prompt_definitions"].documents[0]
        self.assertEqual(document["active_version"], 1)
        self.assertEqual(sum(item["status"] == "ACTIVE" for item in document["versions"]), 1)
        self.assertEqual((document["versions"][0]["status"], document["versions"][1]["status"]), ("ACTIVE", "INACTIVE"))
        resolved = await prompt_registry_service.get_active("BUG_INTERPRETER")
        self.assertEqual((resolved["source"], resolved["resolved_version"]), ("DATABASE", 1))

    async def test_active_is_immutable_and_invalid_identifiers_fail(self):
        await prompt_registry_service.create_draft("BUG_INTERPRETER", "owner@example.com")
        await prompt_registry_service.activate_version("BUG_INTERPRETER", 1)
        with self.assertRaises(HTTPException) as active_error:
            await prompt_registry_service.update_draft("BUG_INTERPRETER", 1, BUG_INTERPRETER_SYSTEM_PROMPT + "\nChange")
        self.assertEqual(active_error.exception.status_code, 409)
        for operation in (prompt_registry_service.get_active("UNKNOWN"), prompt_registry_service.activate_version("BUG_INTERPRETER", 99)):
            with self.assertRaises(HTTPException): await operation

    async def test_prompt_records_and_api_contain_no_configured_credentials(self):
        with patch.object(settings, "openai_api_key", "sk-this-is-a-real-looking-secret-123"), patch.object(settings, "llm_secret_master_key", "master-secret-value"):
            await prompt_registry_service.create_draft("BUG_INTERPRETER", "owner@example.com")
            with self.assertRaises(HTTPException):
                await prompt_registry_service.update_draft("BUG_INTERPRETER", 1, BUG_INTERPRETER_SYSTEM_PROMPT + "\nsk-this-is-a-real-looking-secret-123")
        serialized = str(await prompt_registry_service.get_prompt_definition("BUG_INTERPRETER"))
        self.assertNotIn("sk-this-is-a-real-looking-secret-123", serialized); self.assertNotIn("master-secret-value", serialized)


if __name__ == "__main__": unittest.main()
