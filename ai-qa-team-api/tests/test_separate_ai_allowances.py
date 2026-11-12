"""Per-mode allowance tests. Synthetic database/provider; no external requests."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch
import unittest
import test_account_billing as fixtures
from test_account_billing import settings, AIUsageService, AIOperation, AIUsageError, LLMRequest, LLMResponse, LocalCache, Gateway, LLMProviderError
from app.services.ai.ai_usage_policy import get_ai_usage_policy
from app.services.ai_allowance_migration import plan_ai_allowances, apply_ai_allowances
from app.services.ai_allowances import public_pricing, initialize_allowances
from app.models.subscription import Subscription
from app.routes.subscription_routes import router
from fastapi import FastAPI
from fastapi.testclient import TestClient


class SeparateAllowanceTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.AccountBillingTests.setUp

    def separate(self):
        settings.features.separate_ai_allowances = True
        for account in self.db["customer_accounts"].docs:
            initialize_allowances(account["subscription"])
            account["subscription"]["limits"].update({"managed_ai_credits_limit": 1, "byok_ai_requests_limit": 2})

    def service(self, mode="MANAGED", error=None):
        gateway = Gateway(mode=mode, error=error)
        return AIUsageService(database=self.db, redis_backend=LocalCache(), gateway=gateway, now=lambda: self.now), gateway

    async def test_independent_pools_mode_switching_does_not_reset_either(self):
        self.separate()
        managed, _ = self.service(); byok, _ = self.service("BYOK")
        await managed.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
        for _ in range(2): await byok.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
        usage = self.db["customer_accounts"].docs[0]["subscription"]["usage"]
        self.assertEqual((usage["managed_ai_credits_used"], usage["byok_ai_requests_used"], usage["ai_gen_used"]), (1, 2, 3))
        for service in (managed, byok):
            with self.assertRaises(AIUsageError): await service.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
        self.assertEqual(self.db["ai_usage_records"].docs[-1]["usage_unit"], "BYOK_AI_REQUEST")

    async def test_resolved_provider_mode_selects_bucket_not_client_model(self):
        self.separate(); service, _ = self.service("MANAGED")
        await service.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic", model="BYOK"))
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["byok_ai_requests_used"], 0)

    async def test_simultaneous_users_share_the_same_mode_limit(self):
        self.separate()
        self.db["projects"].docs.append({"project_id": "P3", "account_id": "ACC_one", "created_by": self.owner["email"]})
        service, gateway = self.service()
        outcomes = await asyncio.gather(*[service.execute(AIOperation.TEST_DESIGN, project, dict(user), LLMRequest(prompt="synthetic")) for project, user in (("P1", self.member), ("P3", self.owner))], return_exceptions=True)
        self.assertEqual(sum(isinstance(value, LLMResponse) for value in outcomes), 1)
        self.assertEqual(len(gateway.requests), 1)

    async def test_byok_auth_failure_refunds_only_its_pool_timeout_counts(self):
        self.separate(); managed, _ = self.service()
        await managed.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
        for code, expected in (("AUTHENTICATION_ERROR", 0), ("TIMEOUT", 1)):
            byok, _ = self.service("BYOK", LLMProviderError(code, "synthetic"))
            with self.assertRaises(LLMProviderError): await byok.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
            usage = self.db["customer_accounts"].docs[0]["subscription"]["usage"]
            self.assertEqual((usage["managed_ai_credits_used"], usage["byok_ai_requests_used"]), (1, expected))

    async def test_byok_is_one_request_even_when_managed_policy_is_weighted(self):
        self.separate(); byok, _ = self.service("BYOK")
        with patch.object(settings.ai_usage, "bug_interpreter_credit_cost", 3):
            await byok.execute(AIOperation.BUG_INTERPRETER, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["byok_ai_requests_used"], 1)

    async def test_month_rollover_resets_both_once_and_late_old_request_cannot_reset_backwards(self):
        self.separate()
        subscription = self.db["customer_accounts"].docs[0]["subscription"]
        subscription["ai_usage_period_start"] = "2026-10-01T00:00:00+00:00"
        subscription["usage"].update({"managed_ai_credits_used": 8, "byok_ai_requests_used": 8})
        service, _ = self.service()
        await service.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
        self.assertEqual((subscription["usage"]["managed_ai_credits_used"], subscription["usage"]["byok_ai_requests_used"]), (1, 0))
        with self.assertRaises(AIUsageError): await service._reserve("ACC_one", get_ai_usage_policy(AIOperation.TEST_DESIGN), datetime(2026, 10, 31, tzinfo=timezone.utc), mode="BYOK")
        self.assertEqual(subscription["ai_usage_period_start"], "2026-11-01T00:00:00+00:00")
        self.assertEqual(subscription["usage"]["managed_ai_credits_used"], 1)

    async def test_flag_requires_migration_without_resetting_legacy_usage(self):
        settings.features.separate_ai_allowances = True
        before = deepcopy(self.db["customer_accounts"].docs[0])
        service, gateway = self.service()
        with self.assertRaises(AIUsageError) as error: await service.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
        self.assertEqual(error.exception.code, "AI_ALLOWANCE_MIGRATION_REQUIRED")
        self.assertEqual(before, self.db["customer_accounts"].docs[0]); self.assertEqual(gateway.requests, [])

    async def test_migration_preserves_unknown_usage_and_is_repeatable(self):
        accounts = self.db["customer_accounts"].docs[:1]
        accounts[0]["subscription"]["usage"]["ai_gen_used"] = 3
        records = [{"account_id": "ACC_one", "status": "SUCCEEDED", "ai_mode": mode, "credits_consumed": 1, "billing_period_start": "2026-11-01T00:00:00+00:00"} for mode in ("MANAGED", "BYOK")]
        plan = plan_ai_allowances(accounts, self.db["projects"].docs, records, now=self.now)
        self.assertEqual(plan["errors"], [])
        target = plan["changes"][0]["after"]
        self.assertEqual((target["usage"]["managed_ai_credits_used"], target["usage"]["byok_ai_requests_used"]), (2, 2))
        self.assertEqual(target["ai_allowance_migration"]["unknown_units"], 1)
        with self.assertRaises(ValueError): await apply_ai_allowances(self.db, plan, plan["plan_digest"])
        await apply_ai_allowances(self.db, plan, plan["plan_digest"], maintenance_confirmed=True)
        self.assertEqual(plan_ai_allowances(accounts, [], [], now=self.now)["changes"], [])

    async def test_migration_blocks_unfinished_and_conditional_apply_rejects_changed_usage(self):
        accounts = self.db["customer_accounts"].docs[:1]
        self.assertTrue(plan_ai_allowances(accounts, [], [{"account_id": "ACC_one", "status": "STARTED"}], now=self.now)["errors"])
        plan = plan_ai_allowances(accounts, [], [], now=self.now)
        accounts[0]["subscription"]["usage"]["ai_gen_used"] = 9
        with self.assertRaises(ValueError): await apply_ai_allowances(self.db, plan, plan["plan_digest"], maintenance_confirmed=True)

    async def test_pricing_is_public_uses_configured_limits_and_exposes_no_secrets(self):
        app = FastAPI(); app.include_router(router)
        with patch.object(settings.ai_allowances, "pro_byok", 777):
            response = TestClient(app).get('/auth/pricing')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["byok"]["byok_ai_requests_limit"], 777)
        self.assertFalse(response.json()["billing_enabled"])
        for word in ("smtp_password", "access_key", "mongo_uri", "credential_ref"): self.assertNotIn(word, response.text)
        model = Subscription(); model.apply_plan_defaults()
        self.assertEqual(model.limits.managed_ai_credits_limit, 25)
        self.assertEqual(public_pricing()["enterprise"]["managed_ai_credits_limit"], 5000)


if __name__ == "__main__": unittest.main()
