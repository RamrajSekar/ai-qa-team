"""Synthetic local tests. No real MongoDB, credentials or provider calls."""
import base64
import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "env_tests",
            "REDIS_HOST": "localhost", "REDIS_PORT": "6379", "REDIS_USERNAME": "test",
            "REDIS_PASSWORD": "test", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}
with patch.dict(os.environ, TEST_ENV):
    from app.models.environment_model import ProjectEnvironment
    from app.services import project_environment_service as service
    from app.services.secrets import environment_secrets as secrets
    from app.routes import environment_routes

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


class EnvironmentSecretTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = {"email": "owner@example.test"}
        self.document = None
        self.collection = MagicMock()
        self.collection.insert_one = AsyncMock(side_effect=self.insert)
        self.collection.find_one = AsyncMock(side_effect=lambda query: copy.deepcopy(self.document))
        self.collection.update_one = AsyncMock(side_effect=self.update)
        self.collection.delete_one = AsyncMock(side_effect=self.delete)
        self.collection.find.return_value.to_list = AsyncMock(side_effect=lambda limit: [copy.deepcopy(self.document)])
        database = MagicMock()
        database.__getitem__.side_effect = lambda name: self.collection if name == "environments" else MagicMock(update_one=AsyncMock())
        self.patches = [patch.object(service, "db", database),
                        patch.object(service, "get_next_sequence", new=AsyncMock(return_value="ENV1")),
                        patch.object(service, "require_project_admin", new=AsyncMock(side_effect=self.authorize)),
                        patch.object(service, "require_project_member", new=AsyncMock(side_effect=self.authorize)),
                        patch.object(secrets.settings, "environment_secret_master_key", base64.urlsafe_b64encode(b"e" * 32).decode())]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    async def authorize(self, project, user):
        if project != "P":
            raise HTTPException(404, "Access denied")

    async def insert(self, document):
        self.document = {**copy.deepcopy(document), "_id": "object1"}
        return MagicMock(inserted_id="object1")

    async def update(self, query, update):
        revision = query.get("revision")
        matches = revision == self.document.get("revision") or (revision == {"$exists": False} and "revision" not in self.document)
        if matches:
            self.document.update(copy.deepcopy(update["$set"]))
        return MagicMock(matched_count=int(matches))

    async def delete(self, query):
        self.document = None
        return MagicMock(deleted_count=1)

    def payload(self, **changes):
        return ProjectEnvironment(**{"project_id": "P", "base_url": "https://sandbox.example.test",
                                     "auth_type": "bearer", "auth_token": "synthetic-token",
                                     "credentials": [{"role": "qa", "username": "synthetic-user", "password": "synthetic-password"}], **changes})

    async def create(self):
        return await service.create_environment(self.payload(), self.user)

    async def test_encrypted_roundtrip_and_all_public_reads_are_masked(self):
        created = await self.create()
        for output in (created.model_dump(), (await service.get_environment("ENV1", self.user)).model_dump(),
                       (await service.list_environments("P", self.user))[0]):
            self.assertNotIn("synthetic-password", str(output))
            self.assertNotIn("synthetic-token", str(output))
            self.assertNotIn("secret_payload", output)
            self.assertEqual(output["credentials"][0]["password"], "")
            self.assertTrue(output["credentials"][0]["password_configured"])
        self.assertNotIn("synthetic-password", str(self.document))
        self.assertNotIn("synthetic-token", str(self.document))
        resolved = await service.resolve_environment_credentials("P", "ENV1", "QA", self.user)
        self.assertEqual(resolved["password"], "synthetic-password")
        self.assertEqual(resolved["auth_token"], "synthetic-token")

    async def test_blank_edit_preserves_rotation_revocation_and_stale_rejection(self):
        public = (await self.create()).model_dump()
        public["env_type"] = "staging"
        updated = await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertEqual(secrets.read_secrets(self.document)["passwords"]["qa"], "synthetic-password")
        with self.assertRaises(HTTPException) as stale:
            await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertEqual(stale.exception.status_code, 409)
        public = updated.model_dump()
        public["credentials"][0]["password"] = "synthetic-replacement"
        public["clear_auth_token"] = True
        updated = await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertEqual(secrets.read_secrets(self.document)["passwords"]["qa"], "synthetic-replacement")
        self.assertIsNone(secrets.read_secrets(self.document)["auth_token"])
        public = updated.model_dump()
        public["credentials"] = []
        await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertIsNone(self.document["secret_payload"])

    async def test_identity_changes_require_password_and_role_rename_preserves_it(self):
        public = (await self.create()).model_dump()
        public["credentials"][0]["username"] = "different-user"
        with self.assertRaises(HTTPException) as invalid:
            await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertEqual(invalid.exception.status_code, 422)
        public["credentials"][0]["username"] = "synthetic-user"
        public["credentials"][0]["role"] = "reviewer"
        await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertEqual(secrets.read_secrets(self.document)["passwords"]["reviewer"], "synthetic-password")

    async def test_legacy_read_redacts_and_edit_encrypts_without_bulk_migration(self):
        self.document = {**self.payload().model_dump(), "env_id": "ENV1", "_id": "object1"}
        self.document.pop("revision")
        public = (await service.get_environment("ENV1", self.user)).model_dump()
        self.assertNotIn("synthetic-password", str(public))
        self.assertNotIn("synthetic-token", str(public))
        await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertIn("secret_payload", self.document)
        self.assertNotIn("synthetic-password", str(self.document))

    async def test_missing_key_and_tampered_scope_fail_closed(self):
        with patch.object(secrets.settings, "environment_secret_master_key", None), patch.object(secrets.settings, "llm_secret_master_key", None):
            with self.assertRaises(HTTPException) as missing:
                await self.create()
            self.assertEqual(missing.exception.status_code, 503)
            self.collection.insert_one.assert_not_awaited()
        await self.create()
        copied = {**self.document, "project_id": "FOREIGN"}
        with self.assertRaises(HTTPException):
            secrets.read_secrets(copied)
        with self.assertRaises(HTTPException):
            await service.resolve_environment_credentials("FOREIGN", "ENV1", "qa", self.user)

    async def test_duplicate_roles_and_wrong_key_do_not_disclose_values(self):
        payload = self.payload()
        payload.credentials.append(payload.credentials[0].model_copy())
        with self.assertRaises(HTTPException) as invalid:
            await service.create_environment(payload, self.user)
        self.assertEqual(invalid.exception.status_code, 422)
        await self.create()
        with patch.object(secrets.settings, "environment_secret_master_key", base64.urlsafe_b64encode(b"z" * 32).decode()):
            public = await service.get_environment("ENV1", self.user)
            self.assertEqual(public.credentials[0].password, "")
            with self.assertRaises(HTTPException) as wrong_key:
                await service.resolve_environment_credentials("P", "ENV1", "qa", self.user)
            self.assertEqual(wrong_key.exception.status_code, 503)
            self.assertNotIn("synthetic-password", str(wrong_key.exception))

    async def test_update_race_and_delete(self):
        public = (await self.create()).model_dump()
        self.collection.update_one.side_effect = None
        self.collection.update_one.return_value = MagicMock(matched_count=0)
        original = copy.deepcopy(self.document)
        with self.assertRaises(HTTPException) as race:
            await service.update_environment("ENV1", ProjectEnvironment(**public), self.user)
        self.assertEqual(race.exception.status_code, 409)
        self.assertEqual(self.document, original)
        await service.delete_environment("ENV1", self.user)
        self.assertIsNone(self.document)

    async def test_validation_errors_do_not_echo_credentials(self):
        app = FastAPI()
        app.include_router(environment_routes.router)
        app.dependency_overrides[environment_routes.get_current_user] = lambda: self.user
        with TestClient(app) as client:
            response = client.post("/environments", json={"project_id": "P", "base_url": "https://example.test",
                                   "credentials": [{"password": "synthetic-must-not-echo"}]})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("synthetic-must-not-echo", response.text)
        self.assertNotIn('"input"', response.text)
