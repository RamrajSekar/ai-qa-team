"""Pure policy/authorization checks; no application database or provider calls."""
import os
import unittest
from copy import deepcopy
from unittest.mock import patch, AsyncMock

ENV = {"MONGO_URI": "mongodb://127.0.0.1:27129", "MONGO_DB": "qa_policy_contracts",
    "REDIS_HOST": "127.0.0.1", "REDIS_PORT": "6399", "REDIS_USERNAME": "", "REDIS_PASSWORD": "",
    "JWT_SECRET_KEY": "fixture-only", "SESSION_SECRET_KEY": "fixture-only"}
with patch.dict(os.environ, ENV):
    from app.config import settings, PricingSettings, AIAllowanceSettings
    from app.app_config.plan_limits import plan_limits, PLAN_LIMITS
    from app.models.subscription import Subscription
    from app.services.account_entitlements import plan_entitlements, apply_entitlements
    from app.services.testcase_allowances import effective_subscription, testcase_allowances
    from app.services import subscription_services
    from app.routes import subscription_routes

from fastapi import HTTPException, Request


def account():
    model = Subscription(); model.apply_plan_defaults()
    sub = model.model_dump()
    sub.update(ai_allowance_version=1, ai_usage_period_start="2026-11-01T00:00:00+00:00",
        ai_usage_period_end="2026-12-01T00:00:00+00:00", ai_allowance_migration={"unknown_units": 1})
    sub["usage"].update(managed_ai_credits_used=7, byok_ai_requests_used=3, ai_gen_used=10)
    return {"_id": "ACC_fixture", "status": "ACTIVE", "billing_version": 1,
        "owner_user_id": "fixture-owner", "subscription": sub}


class AccountEntitlementTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for key, value in (("pricing", PricingSettings()), ("ai_allowances", AIAllowanceSettings(free_managed=50, free_byok=50))):
            context = patch.object(settings, key, value); context.start(); self.addCleanup(context.stop)

    def test_team_business_defaults_and_legacy_compatibility(self):
        for name, users, cases, ai in (("team", 5, 3000, 500), ("business", 15, 15000, 2000)):
            model = Subscription(plan=name); model.apply_plan_defaults()
            self.assertEqual(model.limits.team_members_limit, users - 1)
            self.assertEqual(model.limits.testcases_limit, cases)
            self.assertEqual(model.limits.testcases_advanced_limit, cases)
            self.assertEqual(model.limits.managed_ai_credits_limit, ai)
            self.assertEqual(model.entitlement_version, 2)
        self.assertEqual(plan_limits("pro"), PLAN_LIMITS["pro"])
        self.assertEqual(Subscription(plan="enterprise").plan, "enterprise")

    def test_upgrade_preserves_usage_period_status_and_history(self):
        row = account(); before = deepcopy(row)
        result = plan_entitlements([row], {row["_id"]: "team"})
        self.assertFalse(result["errors"])
        after = result["changes"][0]["after"]
        for key in ("usage", "ai_usage_period_start", "ai_usage_period_end", "ai_allowance_migration", "start_date", "status"):
            self.assertEqual(after[key], before["subscription"][key])
        self.assertEqual(row, before)
        self.assertEqual(after["limits"]["executions_limit"], before["subscription"]["limits"]["executions_limit"])

    def test_downgrade_keeps_over_capacity_data_and_repeat_is_empty(self):
        row = account(); row["subscription"]["usage"].update(testcases_used=12, testcases_advanced_used=12, team_members_used=4)
        plan = plan_entitlements([row], {row["_id"]: "free"})
        change = plan["changes"][0]
        self.assertEqual(change["over_capacity"]["testcases_limit"], 12)
        self.assertEqual(change["over_capacity"]["team_members_limit"], 4)
        row["subscription"] = change["after"]
        self.assertEqual(plan_entitlements([row], {row["_id"]: "free"})["changes"], [])

    def test_no_implicit_pro_mapping_or_foreign_account_selection(self):
        row = account(); row["subscription"]["plan"] = "pro"
        self.assertEqual(plan_entitlements([row], {})["changes"], [])
        self.assertTrue(plan_entitlements([row], {"ACC_other": "team"})["errors"])
        self.assertTrue(plan_entitlements([row], {row["_id"]: "enterprise"})["errors"])

    def test_pending_unknown_and_invalid_usage_block_adoption(self):
        for mutate in (lambda r: r.update(resource_quota_pending={"scenarios_used": 1}),
                lambda r: r["subscription"]["usage"].pop("stories_used"),
                lambda r: r["subscription"]["usage"].update(stories_used=-1),
                lambda r: r["subscription"].update(ai_allowance_version=None)):
            row = account(); mutate(row)
            self.assertTrue(plan_entitlements([row], {row["_id"]: "team"})["errors"])

    async def test_unreviewed_or_tampered_apply_never_touches_database(self):
        row = account(); plan = plan_entitlements([row], {row["_id"]: "team"})
        for digest, maintenance in (("stale", True), (plan["plan_digest"], False)):
            with self.assertRaises(ValueError):
                await apply_entitlements(None, plan, digest, maintenance_confirmed=maintenance)
        plan["changes"][0]["after"]["limits"]["stories_limit"] = 9999
        with self.assertRaises(ValueError):
            await apply_entitlements(None, plan, plan["plan_digest"], maintenance_confirmed=True)

    def test_config_changes_require_new_review_and_do_not_rewrite_saved_policy(self):
        row = account(); first = plan_entitlements([row], {row["_id"]: "team"})
        settings.pricing.team.testcases_limit = 4000
        second = plan_entitlements([row], {row["_id"]: "team"})
        self.assertNotEqual(first["plan_digest"], second["plan_digest"])
        model = Subscription(**first["changes"][0]["after"]); model.apply_plan_defaults()
        self.assertEqual(model.limits.testcases_limit, 3000)

    def test_shared_complexity_read_is_pure_and_preserves_pro(self):
        row = account(); change = plan_entitlements([row], {row["_id"]: "business"})["changes"][0]
        effective = effective_subscription(change["after"])
        self.assertEqual(effective["testcase_complexity_policy"], "SHARED_TOTAL")
        self.assertEqual(effective["limits"]["testcases_medium_limit"], 15000)
        legacy = {"plan": "pro", "limits": {"testcases_basic_limit": 5, "testcases_medium_limit": 2}}
        self.assertEqual(effective_subscription(legacy), legacy)

    def test_versioned_zero_total_cannot_expand_from_old_tier_caps(self):
        sub = {"plan":"team", "entitlement_version":2, "limits":{"testcases_limit":0,"testcases_basic_limit":10}}
        self.assertEqual(testcase_allowances(sub)["testcases_limit"], 0)
        sub["limits"].pop("testcases_limit")
        with self.assertRaises(HTTPException): testcase_allowances(sub)

    async def test_no_public_paid_activation_for_legacy_or_account_users(self):
        with self.assertRaises(HTTPException) as error:
            await subscription_routes.upgrade_plan("business", {"email": "owner@example.com", "account_role": "OWNER"})
        self.assertEqual(error.exception.status_code, 403)
        with patch.object(subscription_services, "account_target", new=AsyncMock()) as lookup:
            with self.assertRaises(HTTPException): await subscription_services.upgrade_plan("fixture", "team")
            lookup.assert_not_called()

    async def test_over_capacity_policy_allows_reads_edits_and_review_but_not_creation(self):
        from app.utils import subscription_dependency
        row = account(); sub = plan_entitlements([row], {row["_id"]: "free"})["changes"][0]["after"]
        sub.update(billing_scope="ACCOUNT")
        sub["usage"]["scenarios_used"] = 20
        dependency = subscription_dependency.subscription_required("scenarios")
        with patch.object(subscription_dependency, "get_subscription", new=AsyncMock(return_value=sub)):
            user = {"email": "fixture@example.com"}
            for method in ("GET", "PATCH", "PUT", "DELETE"):
                self.assertEqual(await dependency(user, Request({"type": "http", "method": method})), user)
            with self.assertRaises(HTTPException) as error:
                await dependency(user, Request({"type": "http", "method": "POST"}))
            self.assertEqual(error.exception.status_code, 403)

    async def test_unqualified_legacy_import_cannot_bypass_versioned_limits(self):
        from app.routes import integration_routes
        users = AsyncMock(); users.find_one.return_value = {"integrations": {"github": {"access_token": "fixture-only"}}}
        projects = AsyncMock(); projects.find_one.return_value = {"project_id": "P1", "account_id": "ACC_fixture"}
        accounts = AsyncMock(); accounts.find_one.return_value = {"subscription": {"entitlement_version": 2}}
        with patch.object(integration_routes, "db", {"users": users, "projects": projects, "customer_accounts": accounts}), \
                patch.object(integration_routes, "import_playwright_tests", new=AsyncMock()) as importer:
            payload = integration_routes.ImportRequest(repo_url="https://example.com/fixture", project_id="P1")
            with self.assertRaises(HTTPException) as error:
                await integration_routes.import_playwright_route("github", payload, {"email": "fixture@example.com"})
            self.assertEqual(error.exception.status_code, 409)
            importer.assert_not_called()
