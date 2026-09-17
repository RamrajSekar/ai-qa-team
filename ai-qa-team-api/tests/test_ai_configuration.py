import base64
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "ai_tests", "REDIS_HOST": "localhost", "REDIS_PORT": "6379",
    "REDIS_USERNAME": "test", "REDIS_PASSWORD": "test", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test", "OPENAI_API_KEY": ""}

with patch.dict(os.environ, TEST_ENV):
    from app.models.ai_configuration_model import AIConfigurationInput
    from app.routes import ai_configuration_routes
    from app.services.ai import ai_configuration_service
    from app.services.ai.base_provider import LLMProviderError, LLMRequest
    from app.services.ai.llm_gateway import LLMGateway
    from app.services.ai.openai_provider import OpenAIProvider
    from app.services.ai.azure_openai_provider import AzureOpenAIProvider
    from app.services.ai.provider_errors import normalize_provider_error
    from app.services.ai.provider_registry import ProviderRegistry
    from app.services.secrets import encrypted_mongo
    from app.services.secrets.encrypted_mongo import EncryptedMongoSecretStore


class Result:
    def __init__(self, deleted_count=0): self.deleted_count = deleted_count


class Collection:
    def __init__(self): self.documents = []
    async def find_one(self, query): return next((d for d in self.documents if all(d.get(k) == v for k, v in query.items())), None)
    async def insert_one(self, document): self.documents.append(document.copy())
    async def update_one(self, query, update, upsert=False):
        item = await self.find_one(query)
        if item: item.update(update.get("$set", {}))
        elif upsert: self.documents.append({**query, **update.get("$set", {})})
    async def delete_one(self, query):
        item = await self.find_one(query)
        if item: self.documents.remove(item); return Result(1)
        return Result()


class DB(dict):
    def __missing__(self, key): self[key] = Collection(); return self[key]


class Provider:
    def __init__(self, fail=False): self.fail = fail
    async def validate_connection(self, model=None):
        if self.fail: raise LLMProviderError("AUTHENTICATION_ERROR", "The provider connection could not be validated.")
    async def generate(self, request): return type("Response", (), {"text": "ok", "provider_id": "openai"})()


class AIConfigurationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = DB(); self.key = base64.urlsafe_b64encode(b"k" * 32).decode()
        self.patches = [patch.object(ai_configuration_service, "db", self.db), patch.object(encrypted_mongo, "db", self.db),
            patch.object(ai_configuration_service.settings, "llm_secret_master_key", self.key), patch.object(ai_configuration_service.settings, "openai_api_key", "managed-test-key")]
        for item in self.patches: item.start()

    def tearDown(self):
        for item in reversed(self.patches): item.stop()

    async def test_secret_store_encrypts_and_is_project_bound(self):
        store = EncryptedMongoSecretStore(self.key); ref = await store.put("PRJ1", "sk-secret")
        document = self.db["encrypted_secrets"].documents[0]
        self.assertNotIn("sk-secret", str(document)); self.assertEqual(await store.get("PRJ1", ref), "sk-secret")
        with self.assertRaises(KeyError): await store.get("PRJ2", ref)

    async def test_byok_configuration_stores_only_reference_and_safe_response(self):
        payload = AIConfigurationInput(provider_id="openai", mode="BYOK", model="gpt-4o-mini", api_key="sk-private")
        with patch.object(ai_configuration_service.provider_registry, "resolve", return_value=Provider()):
            response = await ai_configuration_service.activate_configuration("PRJ1", payload, "admin@example.com")
        stored = self.db["ai_configurations"].documents[0]
        self.assertNotIn("api_key", stored); self.assertNotIn("sk-private", str(stored)); self.assertNotIn("credential_ref", response)
        self.assertTrue(response["credential_configured"]); self.assertEqual(response["credential_suffix"], "vate")

    async def test_managed_configuration_never_exposes_platform_key(self):
        payload = AIConfigurationInput(provider_id="managed", mode="MANAGED", model="gpt-4o-mini")
        with (
            patch.object(ai_configuration_service.provider_registry, "resolve", return_value=Provider()) as resolve,
            patch.object(ai_configuration_service, "EncryptedMongoSecretStore", side_effect=AssertionError("Managed mode used SecretStore")),
        ):
            response = await ai_configuration_service.activate_configuration("PRJ1", payload, "admin@example.com")
        self.assertNotIn("managed-test-key", str(response)); self.assertFalse(response["credential_configured"])
        self.assertEqual(resolve.call_args.args[:2], ("openai", "managed-test-key"))

    async def test_managed_frontend_payload_is_accepted_for_test_and_activation(self):
        body = {"provider_id": "managed", "mode": "MANAGED", "model": "gpt-4o-mini", "configuration": {}}
        payload = AIConfigurationInput.model_validate(body)
        self.assertIsNone(payload.api_key)
        with (
            patch.object(ai_configuration_routes, "require_project_admin", new=AsyncMock()),
            patch.object(ai_configuration_routes, "validate_configuration", new=AsyncMock()) as validate,
        ):
            result = await ai_configuration_routes.test_connection("PRJ1", payload, {"email": "admin@example.com"})
        self.assertEqual(result, {"success": True, "code": "CONNECTED"}); validate.assert_awaited_once()
        response = {"project_id": "PRJ1", "provider_id": "managed", "mode": "MANAGED", "model": "gpt-4o-mini",
            "configuration": {}, "status": "ACTIVE", "credential_configured": False, "created_by": "admin@example.com",
            "updated_by": "admin@example.com", "created_at": "now", "updated_at": "now"}
        with (
            patch.object(ai_configuration_routes, "require_project_admin", new=AsyncMock()),
            patch.object(ai_configuration_routes, "activate_configuration", new=AsyncMock(return_value=response)) as activate,
        ):
            self.assertEqual((await ai_configuration_routes.save_and_activate("PRJ1", payload, {"email": "admin@example.com"}))["mode"], "MANAGED")
        activate.assert_awaited_once()

    async def test_openai_and_azure_adapters_validate_with_minimal_requests(self):
        usage = type("Usage", (), {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5})()
        response = type("Completion", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "ok"})()})()], "usage": usage})()
        openai = OpenAIProvider("sk-test", "gpt-test")
        openai.client.chat.completions.create = AsyncMock(return_value=response)
        await openai.validate_connection(); generated = await openai.generate(LLMRequest(prompt="hello"))
        self.assertEqual((generated.provider_id, generated.text, generated.total_tokens), ("openai", "ok", 5))
        structured = LLMRequest(prompt="untrusted", system_prompt="system", response_schema={"type": "object"}, response_schema_name="contract")
        await openai.generate(structured)
        call = openai.client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["messages"], [{"role": "system", "content": "system"}, {"role": "user", "content": "untrusted"}])
        self.assertEqual(call["response_format"]["json_schema"]["name"], "contract")
        azure = AzureOpenAIProvider("key", "https://sample.openai.azure.com", "deployment", "2024-10-21")
        azure.client.chat.completions.create = AsyncMock(return_value=response)
        await azure.validate_connection(); generated = await azure.generate(LLMRequest(prompt="hello"))
        self.assertEqual((generated.provider_id, generated.model), ("azure_openai", "deployment"))

    async def test_failed_switch_preserves_active_configuration_and_secret(self):
        self.db["ai_configurations"].documents.append({"project_id": "PRJ1", "provider_id": "openai", "mode": "BYOK", "credential_ref": "old", "status": "ACTIVE"})
        self.db["encrypted_secrets"].documents.append({"project_id": "PRJ1", "credential_ref": "old", "nonce": "n", "ciphertext": "c"})
        payload = AIConfigurationInput(provider_id="azure_openai", mode="BYOK", configuration={"endpoint": "https://x.openai.azure.com", "deployment": "d", "api_version": "2024-10-21"}, api_key="bad-key")
        with patch.object(ai_configuration_service.provider_registry, "resolve", return_value=Provider(fail=True)):
            with self.assertRaises(LLMProviderError): await ai_configuration_service.activate_configuration("PRJ1", payload, "admin@example.com")
        self.assertEqual(self.db["ai_configurations"].documents[0]["provider_id"], "openai")
        self.assertEqual(len(self.db["encrypted_secrets"].documents), 1)

    async def test_successful_switch_replaces_secret_and_gateway_resolves_project_provider(self):
        with patch.object(ai_configuration_service.provider_registry, "resolve", return_value=Provider()):
            first = AIConfigurationInput(provider_id="openai", mode="BYOK", model="gpt-4o-mini", api_key="first-key")
            await ai_configuration_service.activate_configuration("PRJ1", first, "admin@example.com")
            second = AIConfigurationInput(provider_id="azure_openai", mode="BYOK", configuration={"endpoint": "https://x.openai.azure.com", "deployment": "dep", "api_version": "2024-10-21"}, api_key="second-key")
            await ai_configuration_service.activate_configuration("PRJ1", second, "admin@example.com")
        self.assertEqual(len(self.db["encrypted_secrets"].documents), 1)
        with patch("app.services.ai.llm_gateway.db", self.db), patch("app.services.ai.llm_gateway.provider_registry.resolve", return_value=Provider()) as resolve:
            await LLMGateway().generate("PRJ1", LLMRequest(prompt="hello"))
        self.assertEqual(resolve.call_args.args[0], "azure_openai"); self.assertEqual(resolve.call_args.args[1], "second-key")

    async def test_project_authorization_admin_tester_and_unrelated_user(self):
        admin, tester, other = {"email": "admin@example.com"}, {"email": "tester@example.com"}, {"email": "other@example.com"}
        with patch.object(ai_configuration_routes, "require_project_admin", new=AsyncMock()):
            with patch.object(ai_configuration_routes, "activate_configuration", new=AsyncMock(return_value={"ok": True})):
                await ai_configuration_routes.save_and_activate("PRJ1", AIConfigurationInput(provider_id="managed", mode="MANAGED", model="gpt-4o-mini"), admin)
        denied = AsyncMock(side_effect=HTTPException(403, "Project administrator access required"))
        with patch.object(ai_configuration_routes, "require_project_admin", new=denied):
            with self.assertRaises(HTTPException): await ai_configuration_routes.save_and_activate("PRJ1", AIConfigurationInput(provider_id="managed", mode="MANAGED", model="gpt-4o-mini"), tester)
        hidden = AsyncMock(side_effect=HTTPException(404, "Project not found or access denied"))
        with patch.object(ai_configuration_routes, "require_project_member", new=hidden):
            with self.assertRaises(HTTPException): await ai_configuration_routes.read_configuration("PRJ1", other)

    def test_registry_and_normalized_errors(self):
        registry = ProviderRegistry(); factory = Mock(return_value=Provider()); registry.register("future", factory)
        self.assertIsInstance(registry.resolve("future", "secret", "model", {}), Provider)
        error = type("AuthenticationError", (Exception,), {"status_code": 401})("secret must not leak")
        normalized = normalize_provider_error(error)
        self.assertEqual(normalized.code, "AUTHENTICATION_ERROR"); self.assertNotIn("secret", str(normalized))
        self.assertEqual(ai_configuration_service.public_error(normalized).status_code, 400)

    def test_configuration_rejects_secret_inside_generic_configuration(self):
        with self.assertRaises(ValueError): AIConfigurationInput(provider_id="openai", mode="BYOK", model="gpt", configuration={"access_token": "bad"}, api_key="good")


if __name__ == "__main__": unittest.main()
