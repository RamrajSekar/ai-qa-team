"""Opt-in loopback-only payment/spend transaction qualification; no external calls."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(MONGO_URI="mongodb://127.0.0.1:27129", MONGO_DB="qa_billing_fixture_only",
    REDIS_HOST="127.0.0.1", REDIS_PORT="6399", REDIS_USERNAME="", REDIS_PASSWORD="",
    JWT_SECRET_KEY="local-billing-fixture-only", SESSION_SECRET_KEY="local-billing-fixture-only")
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings, FeatureFlags, BillingSettings, ManagedSpendSettings
from app.models.subscription import Subscription
from app.services.account_entitlements import entitlement_limits, inventory_counts
from app.services.ai.managed_spend import ManagedSpend, claim_call, qualified_model, guard_active
from app.services.ai.spend_cutover import plan_cutover, apply_cutover
from app.services.ai.ai_usage_policy import AIUsageError
from app.services.billing.contracts import PaidInvoice
from app.services.billing.service import BillingService
from app.services.billing.access import consumption_allowed
from app.services.resource_quota import fingerprint


class Provider:
    name = "stripe"
    hosted_domains = {"checkout": "checkout.stripe.com", "portal": "billing.stripe.com"}
    def __init__(self): self.invoices = {}; self.subscriptions = {}; self.calls = 0
    async def price(self, identity):
        return {"active": True, "currency": "usd", "unit_amount": 4900, "type": "recurring",
            "recurring": {"interval": "month", "interval_count": 1}, "livemode": False}
    async def create_customer(self, account, operation): return "cus_" + operation
    async def checkout(self, operation, customer):
        self.calls += 1
        return {"id": "cs_" + operation["_id"], "url": "https://checkout.stripe.com/c/pay/fixture"}
    async def paid_invoice(self, identity): return self.invoices[identity]
    async def subscription(self, identity): return self.subscriptions[identity]


async def verify(db):
    checks = []
    async def run(name, work):
        await work(); checks.append(name)
    async def denied(work):
        try: await work
        except (HTTPException, AIUsageError, ValueError): return
        raise AssertionError("Expected rejection")
    spend = ManagedSpend(db)
    model = "gpt-4o-mini-2024-07-18"
    _, pricing = qualified_model(model, 100)
    amount = pricing["reserved_micro_usd"]
    settings.managed_spend.account_monthly_micro_usd = {"free": amount, "team": amount, "business": amount}
    settings.managed_spend.platform_monthly_micro_usd = amount * 2

    async def cutover():
        opening = {"period": datetime.now(timezone.utc).strftime("%Y-%m"), "currency": "USD",
            "provider_report_reference": "synthetic-opening-only", "platform_spent_micro_usd": 0, "accounts": {}}
        plan = await plan_cutover(db, opening)
        await denied(apply_cutover(db, plan, "invalid", maintenance_confirmed=True))
        await apply_cutover(db, plan, plan["plan_digest"], maintenance_confirmed=True)
        assert (await plan_cutover(db, opening))["already_initialized"]
        with patch.object(settings.features, "managed_spend_guard", False): assert await guard_active(db)
    await run("reviewed_cutover_and_flag_off_cannot_reset_policy", cutover)

    async def concurrency():
        results = await asyncio.gather(*(spend.reserve(uuid4().hex, "ACC_race", "free", model, 100) for _ in range(5)), return_exceptions=True)
        rows = [row for row in results if isinstance(row, dict)]
        assert len(rows) == 1, results
        await spend.settle(rows[0], release_unsubmitted=True)
        budget = await db.ai_spend_budgets.find_one({"_id": rows[0]["budget_ids"][0]})
        assert budget["reserved_micro_usd"] == 0
    await run("atomic_account_last_slot_and_presubmission_release", concurrency)

    async def platform():
        rows = await asyncio.gather(*(spend.reserve(uuid4().hex, "ACC_platform" + str(i), "free", model, 100) for i in range(5)), return_exceptions=True)
        accepted = [row for row in rows if isinstance(row, dict)]
        assert len(accepted) == 2
        for row in accepted: await spend.settle(row, release_unsubmitted=True)
    await run("atomic_platform_last_slots_across_accounts", platform)

    async def settle():
        row = await spend.reserve(uuid4().hex, "ACC_settle", "free", model, 100)
        await spend.submitted(row)
        request = SimpleNamespace(spend_reservation_id=row["_id"], max_retries=0, max_tokens=100)
        context = SimpleNamespace(mode="MANAGED", model=model)
        await claim_call(db, context, request)
        await denied(claim_call(db, context, request))
        await spend.settle(row, input_tokens=100, output_tokens=10, response_model=model)
        await spend.settle(row, input_tokens=100, output_tokens=10, response_model=model)
        saved = await db.ai_spend_reservations.find_one({"_id": row["_id"]})
        budget = await db.ai_spend_budgets.find_one({"_id": row["budget_ids"][0]})
        assert saved["state"] == "SETTLED" and budget["spent_micro_usd"] == saved["actual_micro_usd"]
    await run("single_provider_admission_and_idempotent_measured_settlement", settle)

    async def unknown():
        row = await spend.reserve(uuid4().hex, "ACC_unknown", "free", model, 100)
        await spend.submitted(row); await spend.unknown(row)
        await spend.settle(row, release_unsubmitted=True)
        assert (await db.ai_spend_reservations.find_one({"_id": row["_id"]}))["state"] == "UNKNOWN"
        await denied(spend.reserve(uuid4().hex, "ACC_unknown", "free", model, 100))
        await spend.settle(row, input_tokens=1, output_tokens=1, response_model=model,
            proof={"record_digest": fingerprint(await db.ai_spend_reservations.find_one({"_id": row["_id"]})), "reference": "fixture"})
    await run("uncertain_spend_stays_held_until_digest_reviewed_evidence", unknown)

    async def gateway_flow():
        from bson import ObjectId
        from app.services.ai.ai_usage_service import AIUsageService
        from app.services.ai.ai_usage_policy import AIOperation
        from app.services.ai.base_provider import LLMRequest, LLMResponse, LLMProviderError
        from app.services.ai.llm_gateway import LLMGateway, ResolvedLLMContext
        from app.utils.redis_client import LocalCache
        identity = "ACC_" + uuid4().hex
        actor = {"_id": ObjectId(), "email": uuid4().hex + "@example.com", "account_id": identity,
            "account_state": "ACTIVE", "account_role": "OWNER"}
        sub = Subscription(); sub.apply_plan_defaults(); sub = sub.model_dump()
        sub.update(ai_allowance_version=1, entitlement_version=2)
        sub["limits"] = entitlement_limits(sub, "free")
        await db.users.insert_one(actor)
        await db.customer_accounts.insert_one({"_id": identity, "status": "ACTIVE", "billing_version": 1, "subscription": sub})
        project = "P_" + uuid4().hex
        await db.projects.insert_one({"project_id": project, "account_id": identity, "created_by": actor["email"]})
        class SyntheticProvider:
            requests = []
            async def generate(self, request):
                self.requests.append(request)
                assert request.max_retries == 0 and request.spend_reservation_id and request.model == model
                return LLMResponse("synthetic", "openai", model, 10, 2, 12)
        synthetic = SyntheticProvider()
        class Gateway(LLMGateway):
            async def resolve(self, project_id, request): return ResolvedLLMContext("MANAGED", "openai", "gpt-4o-mini", synthetic)
        service = AIUsageService(database=db, redis_backend=LocalCache(), gateway=Gateway())
        with patch("app.services.ai.llm_gateway.db", db), patch.object(settings, "app_env", "test"):
            await service.execute(AIOperation.KNOWLEDGE_ASK, project, actor, LLMRequest("synthetic", max_tokens=100))
            assert len(synthetic.requests) == 1
            record = await db.ai_spend_reservations.find_one({"_id": synthetic.requests[0].spend_reservation_id})
            assert record["state"] == "SETTLED"
            account = await db.customer_accounts.find_one({"_id": identity})
            assert account["subscription"]["usage"]["managed_ai_credits_used"] == 1
            with patch.object(settings.managed_spend, "account_monthly_micro_usd", {"free": 1}):
                await denied(service.execute(AIOperation.KNOWLEDGE_ASK, project, actor, LLMRequest("synthetic", max_tokens=100)))
            assert len(synthetic.requests) == 1
    await run("real_usage_service_gateway_admission_settlement_and_pre_provider_budget_stop", gateway_flow)

    async def anomaly():
        row = await spend.reserve(uuid4().hex, "ACC_anomaly", "free", model, 100)
        await spend.submitted(row)
        await denied(spend.settle(row, input_tokens=1, output_tokens=101, response_model=model))
        assert (await db.ai_spend_control.find_one({"_id": "managed"}))["halted"]
        await denied(spend.reserve(uuid4().hex, "ACC_other", "free", model, 100))
        # Only this synthetic fixture resets its own halt for independent billing cases.
        await db.ai_spend_control.update_one({"_id": "managed"}, {"$set": {"halted": False}})
    await run("provider_bound_anomaly_halts_further_managed_calls", anomaly)

    provider = Provider(); billing = BillingService(db, provider)
    async def fixture():
        identity = "ACC_" + uuid4().hex
        sub = Subscription(); sub.apply_plan_defaults(); sub = sub.model_dump()
        sub.update(entitlement_version=2, ai_allowance_version=1)
        sub["limits"] = entitlement_limits(sub, "free")
        sub["usage"].update(managed_ai_credits_used=7, byok_ai_requests_used=3)
        row = {"_id": identity, "status": "ACTIVE", "billing_version": 1, "subscription": sub}
        await db.customer_accounts.insert_one(row)
        await billing.checkout(row, {"_id": "fixture-owner"}, "team", uuid4().hex)
        operation = await db.billing_checkout_operations.find_one({"account_id": identity})
        invoice_id, subscription_id = "in_" + uuid4().hex, "sub_" + uuid4().hex
        provider.invoices[invoice_id] = PaidInvoice("stripe", invoice_id, operation["customer_id"], subscription_id,
            operation["price_id"], 4900, 4900, "usd", int(datetime.now(timezone.utc).timestamp()) + 86400, False, True, "subscription_create")
        provider.subscriptions[subscription_id] = {"status": "active", "livemode": False, "cancel_at_period_end": False}
        return row, operation, invoice_id, subscription_id

    async def payment():
        row, operation, invoice, subscription = await fixture()
        before = deepcopy(row["subscription"]["usage"])
        count = provider.calls
        await billing.checkout(row, {"_id": "fixture-owner"}, "team", operation["request_id"])
        assert provider.calls == count
        await denied(billing.checkout(row, {"_id": "fixture-owner"}, "team", uuid4().hex))
        results = await asyncio.gather(*(billing.paid("evt_" + uuid4().hex, invoice) for _ in range(4)), return_exceptions=True)
        assert sum(result == {"applied": True} for result in results) == 1, results
        saved = await db.customer_accounts.find_one({"_id": row["_id"]})
        assert saved["subscription"]["plan"] == "team" and saved["subscription"]["usage"] == before
        assert consumption_allowed(saved)
        provider.subscriptions[subscription].update(status="past_due")
        await billing.subscription_changed("evt_failure", subscription)
        assert consumption_allowed(await db.customer_accounts.find_one({"_id": row["_id"]}))
        provider.subscriptions[subscription].update(status="canceled")
        await billing.subscription_changed("evt_cancel", subscription)
        saved = await db.customer_accounts.find_one({"_id": row["_id"]})
        assert saved["subscription"]["plan"] == "free" and saved["subscription"]["usage"] == before
    await run("checkout_lock_duplicate_payments_failure_and_cancel_preserve_usage", payment)

    async def out_of_order():
        row, operation, invoice, subscription = await fixture()
        provider.subscriptions[subscription]["status"] = "canceled"
        await billing.subscription_changed("evt_beforepaid", subscription)
        await denied(billing.paid("evt_latepaid", invoice))
        assert (await db.customer_accounts.find_one({"_id": row["_id"]}))["subscription"]["plan"] == "free"
        row, operation, invoice, subscription = await fixture()
        await billing.payment_review("evt_refundfirst", invoice, "refund")
        await denied(billing.paid("evt_afterrefund", invoice))
    await run("cancellation_and_refund_before_payment_block_late_grants", out_of_order)

    async def refund():
        row, operation, invoice, subscription = await fixture()
        await billing.paid("evt_pay", invoice)
        await billing.payment_review("evt_refund", invoice, "refund")
        saved = await db.customer_accounts.find_one({"_id": row["_id"]})
        assert saved["billing"]["status"] == "review_required" and not consumption_allowed(saved)
        assert saved["subscription"]["usage"]["managed_ai_credits_used"] == 7
    await run("refund_review_blocks_new_consumption_without_deleting_data", refund)

    async def renewal():
        from dataclasses import replace
        row, operation, invoice, subscription = await fixture()
        await billing.paid("evt_initial", invoice)
        before = (await db.customer_accounts.find_one({"_id": row["_id"]}))["subscription"]["usage"]
        renewed = "in_" + uuid4().hex
        provider.invoices[renewed] = replace(provider.invoices[invoice], invoice_id=renewed, reason="subscription_cycle", paid_until=2000000000)
        await billing.paid("evt_renewal", renewed)
        saved = await db.customer_accounts.find_one({"_id": row["_id"]})
        assert saved["billing"]["paid_until"] == 2000000000 and saved["subscription"]["usage"] == before
        assert not consumption_allowed(saved, now=datetime(2035, 1, 1, tzinfo=timezone.utc))
    await run("renewals_extend_paid_period_without_refilling_used_requests", renewal)

    async def authorization():
        from bson import ObjectId
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from app.routes import billing_routes
        row, operation, invoice, subscription = await fixture()
        identity = ObjectId()
        stored = {"_id": identity, "email": uuid4().hex + "@example.com", "account_id": row["_id"], "account_state": "ACTIVE", "account_role": "MEMBER"}
        await db.users.insert_one(stored)
        # Deliberately stale/elevated JWT claims must lose to stored membership.
        actor = {**stored, "account_role": "OWNER", "account_id": "ACC_foreign", "platform_role": "OWNER"}
        app = FastAPI(); app.include_router(billing_routes.router)
        app.dependency_overrides[billing_routes.get_current_user] = lambda: deepcopy(actor)
        with patch.object(billing_routes, "db", db), patch.object(billing_routes.billing_providers, "resolve", return_value=provider):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://fixture") as client:
                status = await client.get("/account/billing")
                assert status.status_code == 200 and status.headers["cache-control"] == "private, no-store"
                response = await client.post("/account/billing/checkout", json={"plan": "team", "request_id": uuid4().hex})
                assert response.status_code == 403
                response = await client.post("/account/billing/checkout", json={"plan": "team", "request_id": uuid4().hex, "account_id": "ACC_foreign"})
                assert response.status_code == 422
                assert (await client.post("/account/billing/portal")).status_code == 403
    await run("api_reloads_account_role_and_rejects_cross_account_payloads", authorization)

    async def invitations():
        row = {"_id": "ACC_inventory", "owner_user_id": "owner"}
        await db.users.insert_one({"_id": "owner", "email": "owner@example.com", "account_id": row["_id"], "account_state": "ACTIVE"})
        await db.account_invitations.insert_one({"_id": "invite@example.com", "account_id": row["_id"], "status": "PENDING"})
        assert (await inventory_counts(db, row))["team_members_used"] == 1
    await run("pending_invitation_identity_is_counted_without_email_field", invitations)
    return checks


async def main():
    if sys.argv[1:] != ["--confirm-isolated-local"]: raise SystemExit("Use --confirm-isolated-local")
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27129/?replicaSet=qaTestDesign", serverSelectionTimeoutMS=5000)
    name = "qa_billing_" + uuid4().hex
    flags = FeatureFlags(customer_accounts=True, account_subscriptions=True, separate_ai_allowances=True,
        managed_spend_guard=True, billing_checkout=True)
    spend = ManagedSpendSettings(cutover_id="fixture-v1", pricing_revision="synthetic-rates", rates_verified=True,
        per_request_micro_usd=1000000, platform_monthly_micro_usd=1000000,
        account_monthly_micro_usd={"free": 1000000, "team": 1000000, "business": 1000000},
        models={"gpt-4o-mini-2024-07-18": {"input_micro_usd_per_million": 150000, "output_micro_usd_per_million": 600000}})
    config = BillingSettings(stripe_key="sk_test_fixture", stripe_webhook_secret="whsec_fixture",
        app_origin="https://example.com", stripe_price_ids={"team": "price_team", "business": "price_business"})
    try:
        assert (await client.admin.command("hello"))["setName"] == "qaTestDesign"
        with patch.object(settings, "features", flags), patch.object(settings, "managed_spend", spend), patch.object(settings, "billing", config):
            checks = await verify(client[name])
        print(json.dumps({"passed": len(checks), "checks": checks, "database": "ephemeral loopback fixture", "provider": "double; no financial or AI calls"}, indent=2))
    finally:
        await client.drop_database(name); client.close()


if __name__ == "__main__": asyncio.run(main())
