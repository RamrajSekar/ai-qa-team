import asyncio
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEST_ENV = {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "usage_tests", "REDIS_HOST": "localhost", "REDIS_PORT": "6379",
    "REDIS_USERNAME": "test", "REDIS_PASSWORD": "test", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test", "OPENAI_API_KEY": "managed"}

with patch.dict(os.environ, TEST_ENV):
    from app.config import settings
    from app.services.ai.ai_usage_policy import AIOperation, AIUsageError, get_ai_usage_policy
    from app.services.ai.ai_usage_service import AIUsageService
    from app.services.ai.base_provider import LLMProviderError, LLMRequest, LLMResponse
    from app.services.ai.llm_gateway import ResolvedLLMContext
    from app.utils.redis_client import LocalCache


def nested_get(document, path, missing=None):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value: return missing
        value = value[part]
    return value


def nested_set(document, path, value):
    target = document
    parts = path.split(".")
    for part in parts[:-1]: target = target.setdefault(part, {})
    target[parts[-1]] = deepcopy(value)


def matches(document, query):
    for key, expected in query.items():
        actual = nested_get(document, key)
        if isinstance(expected, dict):
            if "$ne" in expected and actual == expected["$ne"]: return False
            if "$lte" in expected and (actual is None or actual > expected["$lte"]): return False
        elif actual != expected: return False
    return True


class Result:
    def __init__(self, modified_count=1): self.modified_count = modified_count


class Collection:
    def __init__(self): self.documents = []; self.lock = asyncio.Lock()
    async def find_one(self, query, projection=None):
        item = next((item for item in self.documents if matches(item, query)), None)
        return deepcopy(item) if item else None
    async def insert_one(self, document): self.documents.append(deepcopy(document)); return Result()
    async def update_one(self, query, update, **_kwargs):
        async with self.lock:
            item = next((item for item in self.documents if matches(item, query)), None)
            if not item: return Result(0)
            for key, value in update.get("$set", {}).items(): nested_set(item, key, value)
            for key, value in update.get("$inc", {}).items(): nested_set(item, key, (nested_get(item, key, 0) or 0) + value)
            return Result()
    async def find_one_and_update(self, query, update, **_kwargs):
        async with self.lock:
            item = next((item for item in self.documents if matches(item, query)), None)
            if not item: return None
            for key, value in update.get("$inc", {}).items(): nested_set(item, key, (nested_get(item, key, 0) or 0) + value)
            return deepcopy(item)


class DB(dict):
    def __missing__(self, key): self[key] = Collection(); return self[key]


class Gateway:
    def __init__(self, *, mode="MANAGED", response=None, error=None, entered=None, release=None):
        self.mode = mode; self.response = response or LLMResponse("ok", "openai", "gpt-test")
        self.error = error; self.requests = []; self.entered = entered; self.release = release
    async def resolve(self, _project_id, _request):
        return ResolvedLLMContext(self.mode, "openai", "gpt-test", None)
    async def generate_resolved(self, _context, request):
        self.requests.append(request)
        if self.entered: self.entered.set()
        if self.release: await self.release.wait()
        if self.error: raise self.error
        return self.response


class AIUsageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        feature_patch = patch.object(settings, "features", settings.features.model_copy(update={"customer_accounts": False, "account_subscriptions": False, "separate_ai_allowances": False}))
        feature_patch.start(); self.addCleanup(feature_patch.stop)
        self.db = DB(); self.redis = LocalCache(); self.now = datetime(2026, 9, 17, tzinfo=timezone.utc)
        self.owner = {"_id": "U1", "email": "owner@example.com", "subscription": {"status": "active", "plan": "free",
            "usage": {"ai_gen_used": 0}, "limits": {"ai_gen_limit": 3}}}
        self.db["users"].documents.append(deepcopy(self.owner))
        self.db["projects"].documents.append({"project_id": "PRJ1", "created_by": "owner@example.com"})

    def service(self, gateway=None):
        return AIUsageService(database=self.db, redis_backend=self.redis, gateway=gateway or Gateway(), now=lambda: self.now)

    async def test_bug_report_draft_uses_existing_meter_and_usage_identity(self):
        await self.service().execute(AIOperation.BUG_REPORT_DRAFT, "PRJ1", self.owner, LLMRequest(prompt="synthetic failure"))
        self.assertEqual(self.db["users"].documents[0]["subscription"]["usage"]["ai_gen_used"], 1)
        self.assertEqual(self.db["ai_usage_records"].documents[0]["operation_type"], "BUG_REPORT_DRAFT")

    def test_known_and_unknown_operation_policy_and_configurable_defaults(self):
        with patch.object(settings.ai_usage, "bug_interpreter_max_input_chars", 123):
            policy = get_ai_usage_policy(AIOperation.BUG_INTERPRETER)
        self.assertEqual((policy.max_input_chars, policy.credit_cost, policy.monthly_allowance), (123, 1, None))
        with self.assertRaises(AIUsageError) as error: get_ai_usage_policy("CLIENT_CHOSEN_CHEAP_OPERATION")
        self.assertEqual(error.exception.code, "AI_OPERATION_UNSUPPORTED")

    async def test_input_guard_and_output_bound_are_pre_provider(self):
        gateway = Gateway(); service = self.service(gateway)
        with patch.object(settings.ai_usage, "bug_interpreter_max_input_chars", 4):
            with self.assertRaises(AIUsageError) as error:
                await service.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="12345"))
        self.assertEqual(error.exception.code, "AI_INPUT_TOO_LARGE"); self.assertFalse(gateway.requests)
        self.assertEqual(nested_get(self.db["users"].documents[0], "subscription.usage.ai_gen_used"), 0)
        with patch.object(settings.ai_usage, "bug_interpreter_max_output_tokens", 25):
            await service.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="ok", model="client-override", max_tokens=999))
        self.assertEqual((gateway.requests[0].max_tokens, gateway.requests[0].model), (25, "gpt-test"))

    async def test_managed_and_byok_are_server_resolved_and_metered(self):
        await self.service(Gateway(mode="MANAGED")).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="one"))
        managed = self.db["ai_usage_records"].documents[-1]
        self.assertEqual((managed["ai_mode"], managed["credits_consumed"], managed["managed_cost_eligible"]), ("MANAGED", 1, True))
        await self.service(Gateway(mode="BYOK")).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="two"))
        byok = self.db["ai_usage_records"].documents[-1]
        self.assertEqual((byok["ai_mode"], byok["credits_consumed"], byok["managed_cost_eligible"], byok["estimated_managed_cost"]), ("BYOK", 1, False, None))

    async def test_atomic_reservation_cannot_overspend_last_credit(self):
        nested_set(self.db["users"].documents[0], "subscription.limits.ai_gen_limit", 1)
        with patch.object(settings.ai_usage, "max_concurrent_requests", 2):
            results = await asyncio.gather(*[
                self.service(Gateway()).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt=str(index)))
                for index in range(2)
            ], return_exceptions=True)
        self.assertEqual(sum(isinstance(result, LLMResponse) for result in results), 1)
        errors = [result for result in results if isinstance(result, AIUsageError)]
        self.assertEqual((len(errors), errors[0].code), (1, "AI_USAGE_LIMIT_EXCEEDED"))
        self.assertEqual(nested_get(self.db["users"].documents[0], "subscription.usage.ai_gen_used"), 1)

    async def test_failure_credit_semantics_are_deterministic(self):
        auth_error = LLMProviderError("AUTHENTICATION_ERROR", "safe")
        with self.assertRaises(LLMProviderError):
            await self.service(Gateway(error=auth_error)).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="x"))
        self.assertEqual(nested_get(self.db["users"].documents[0], "subscription.usage.ai_gen_used"), 0)
        self.assertEqual(self.db["ai_usage_records"].documents[-1]["credits_consumed"], 0)
        with self.assertRaises(LLMProviderError):
            await self.service(Gateway(error=LLMProviderError("TIMEOUT", "safe"))).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="x"))
        self.assertEqual(nested_get(self.db["users"].documents[0], "subscription.usage.ai_gen_used"), 1)
        self.assertEqual(self.db["ai_usage_records"].documents[-1]["credits_consumed"], 1)

    async def test_provider_failure_logging_is_diagnostic_without_request_secrets(self):
        error = LLMProviderError(
            "PROVIDER_REQUEST_INVALID", "safe", status_code=400,
            provider_error_type="invalid_request_error", provider_error_code="invalid_json_schema",
            provider_error_param="response_format",
        )
        request = LLMRequest(
            prompt="private bug text", system_prompt="private system prompt",
            response_schema={"secret-shaped-example": "must not log"}, response_schema_name="test_intent_v1",
        )
        with self.assertLogs("app.services.ai.ai_usage_service", level="WARNING") as captured:
            with self.assertRaises(LLMProviderError):
                await self.service(Gateway(error=error)).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, request)
        output = " ".join(captured.output)
        for expected in ("operation=BUG_INTERPRETER", "provider=openai", "model=gpt-test", "provider_status=400",
                         "error_code=PROVIDER_REQUEST_INVALID", "provider_error_code=invalid_json_schema",
                         "provider_error_param=response_format", "structured_output=True", "schema_name=test_intent_v1", "usage_id=AIU-"):
            self.assertIn(expected, output)
        for secret in ("private bug text", "private system prompt", "secret-shaped-example", "api_key", "credential_ref"):
            self.assertNotIn(secret, output)

    async def test_rate_limit_rejects_without_provider_or_credit(self):
        gateway = Gateway(); service = self.service(gateway)
        with patch.object(settings.ai_usage, "rate_limit_requests", 1):
            await service.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="first"))
            with self.assertRaises(AIUsageError) as error:
                await service.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="second"))
        self.assertEqual(error.exception.code, "AI_RATE_LIMITED"); self.assertEqual(len(gateway.requests), 1)
        self.assertEqual(nested_get(self.db["users"].documents[0], "subscription.usage.ai_gen_used"), 1)

    async def test_concurrency_rejects_and_slot_releases_after_success_and_failure(self):
        nested_set(self.db["users"].documents[0], "subscription.limits.ai_gen_limit", 10)
        entered, release = asyncio.Event(), asyncio.Event(); gateway = Gateway(entered=entered, release=release)
        service = self.service(gateway)
        first = asyncio.create_task(service.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="first")))
        await entered.wait()
        with self.assertRaises(AIUsageError) as error:
            await service.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="second"))
        self.assertEqual(error.exception.code, "AI_CONCURRENCY_LIMIT")
        release.set(); await first
        await service.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="third"))
        failing = self.service(Gateway(error=RuntimeError("do not expose")))
        with self.assertRaises(AIUsageError) as failure:
            await failing.execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="failure"))
        self.assertEqual(failure.exception.code, "AI_PROVIDER_FAILED")
        await self.service(Gateway()).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="after"))

    async def test_token_telemetry_and_missing_usage(self):
        response = LLMResponse("ok", "openai", "gpt", input_tokens=11, output_tokens=7, total_tokens=18)
        await self.service(Gateway(response=response)).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="private bug"))
        record = self.db["ai_usage_records"].documents[-1]
        self.assertEqual((record["input_tokens"], record["output_tokens"], record["total_tokens"]), (11, 7, 18))
        self.assertNotIn("private bug", str(record)); self.assertNotIn("api_key", str(record)); self.assertNotIn("credential_ref", str(record))
        await self.service(Gateway()).execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="no usage"))
        self.assertIsNone(self.db["ai_usage_records"].documents[-1]["total_tokens"])

    async def test_production_does_not_silently_use_process_local_limits(self):
        with patch.object(settings, "app_env", "production"):
            with self.assertRaises(AIUsageError) as error:
                await self.service().execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="x"))
        self.assertEqual(error.exception.code, "AI_LIMITER_UNAVAILABLE")

    async def test_usage_record_shape_and_project_user_isolation(self):
        other = {"_id": "U2", "email": "other@example.com"}
        with self.assertRaises(AIUsageError) as error:
            await self.service().execute(AIOperation.BUG_INTERPRETER, "PRJ1", other, LLMRequest(prompt="x"))
        self.assertEqual(error.exception.code, "AI_ACCESS_DENIED")
        self.db["project_memberships"].documents.append({"project_id": "PRJ1", "email": "other@example.com", "status": "ACTIVE"})
        await self.service().execute(AIOperation.BUG_INTERPRETER, "PRJ1", other, LLMRequest(prompt="x"))
        record = self.db["ai_usage_records"].documents[-1]
        for field in ("usage_id", "project_id", "user_id", "operation_type", "ai_mode", "provider_id", "model", "status", "started_at", "completed_at"):
            self.assertIn(field, record)
        self.assertEqual((record["user_id"], record["billing_owner"]), ("U2", "owner@example.com"))

    async def test_previous_period_usage_resets_lazily(self):
        user = self.db["users"].documents[0]
        nested_set(user, "subscription.usage.ai_gen_used", 3)
        nested_set(user, "subscription.ai_usage_period_start", "2026-08-01T00:00:00+00:00")
        await self.service().execute(AIOperation.BUG_INTERPRETER, "PRJ1", self.owner, LLMRequest(prompt="new month"))
        self.assertEqual(nested_get(user, "subscription.usage.ai_gen_used"), 1)
        self.assertEqual(nested_get(user, "subscription.ai_usage_period_start"), "2026-09-01T00:00:00+00:00")

    def test_errors_are_safe_and_normalized(self):
        error = AIUsageError("AI_RATE_LIMITED", 429, "Too many AI requests. Try again later.")
        self.assertEqual(error.public_detail(), {"code": "AI_RATE_LIMITED", "message": "Too many AI requests. Try again later."})


if __name__ == "__main__": unittest.main()
