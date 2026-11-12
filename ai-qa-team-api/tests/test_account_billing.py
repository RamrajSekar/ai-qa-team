"""Account team/billing tests: synthetic Mongo, auth/provider doubles; no external calls."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
import unittest

from test_customer_accounts import settings, FeatureFlags, CustomerAccounts, account_routes, project_routes, auth_routes, project_team_service, auth_dependency, project_authorization
from test_ai_usage import Gateway, nested_get, nested_set
from app.services import subscription_services, sync_usage
from app.routes import project_team_routes, subscription_routes
from app.services.account_billing import billing_account
from app.services.account_subscription_migration import plan_subscriptions, apply_subscriptions
from app.services.ai.ai_usage_service import AIUsageService
from app.services.ai.ai_usage_policy import AIOperation, AIUsageError
from app.services.ai.base_provider import LLMRequest, LLMResponse, LLMProviderError
from app.utils.redis_client import LocalCache
from app.models.subscription import Subscription
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError


def matches(doc, query):
    for key, expected in query.items():
        if key == "$or":
            if not any(matches(doc, item) for item in expected): return False
            continue
        actual = nested_get(doc, key)
        if isinstance(expected, dict) and any(key.startswith("$") for key in expected):
            for op, target in expected.items():
                if op == "$in" and actual not in target: return False
                if op == "$ne" and actual == target: return False
                if op == "$gt" and (actual is None or not actual > target): return False
                if op == "$gte" and (actual is None or not actual >= target): return False
                if op == "$lt" and (actual is None or not actual < target): return False
                if op == "$lte" and (actual is None or not actual <= target): return False
        elif actual != expected: return False
    return True


class Cursor:
    def __init__(self, docs): self.docs = deepcopy(docs)
    async def to_list(self, limit): return self.docs[:limit] if limit else self.docs


class Collection:
    def __init__(self): self.docs = []
    async def find_one(self, query, *args): return deepcopy(next((doc for doc in self.docs if matches(doc, query)), None))
    def find(self, query, *args): return Cursor([doc for doc in self.docs if matches(doc, query)])
    async def count_documents(self, query): return sum(matches(doc, query) for doc in self.docs)
    async def insert_one(self, doc):
        if any((doc.get("_id") is not None and row.get("_id") == doc["_id"]) or (doc.get("membership_id") and row.get("project_id") == doc.get("project_id") and row.get("email") == doc.get("email")) for row in self.docs):
            raise DuplicateKeyError("synthetic duplicate")
        self.docs.append(deepcopy(doc)); return SimpleNamespace(inserted_id=doc.get("_id"))
    async def update_one(self, query, update, upsert=False):
        doc = next((doc for doc in self.docs if matches(doc, query)), None)
        if doc is None and upsert:
            doc = {**query, **update.get("$setOnInsert", {})}; self.docs.append(doc)
        if doc is None: return SimpleNamespace(matched_count=0, modified_count=0)
        for key, value in update.get("$set", {}).items(): nested_set(doc, key, value)
        for key, value in update.get("$inc", {}).items(): nested_set(doc, key, nested_get(doc, key, 0) + value)
        return SimpleNamespace(matched_count=1, modified_count=1)
    async def update_many(self, query, update):
        count = 0
        for doc in list(self.docs):
            if matches(doc, query):
                await self.update_one({"_id": doc["_id"]}, update); count += 1
        return SimpleNamespace(modified_count=count)
    async def find_one_and_update(self, query, update, **kwargs):
        doc = next((doc for doc in self.docs if matches(doc, query)), None)
        if doc is None: return None
        await self.update_one(query, update)
        return deepcopy(doc)
    async def delete_one(self, query):
        doc = next((doc for doc in self.docs if matches(doc, query)), None)
        if doc is not None: self.docs.remove(doc)
        return SimpleNamespace(deleted_count=int(doc is not None))


class DB(dict):
    def __missing__(self, key): self[key] = Collection(); return self[key]


class AccountBillingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = DB()
        features = FeatureFlags(customer_accounts=True, account_subscriptions=True)
        p = patch.object(settings, "features", features); p.start(); self.addCleanup(p.stop)
        for module in (subscription_services, sync_usage, account_routes, project_routes, auth_routes, project_team_service, auth_dependency, project_authorization, subscription_routes):
            p = patch.object(module, "db", self.db); p.start(); self.addCleanup(p.stop)
        self.now = datetime(2026, 11, 12, tzinfo=timezone.utc)
        model = Subscription(); model.apply_plan_defaults()
        sub = model.model_dump(); sub["limits"].update({"team_members_limit": 3, "ai_gen_limit": 1})
        sub["ai_usage_period_start"] = "2026-11-01T00:00:00+00:00"
        self.owner = {"_id": "U1", "email": "owner@example.com", "account_id": "ACC_one", "account_role": "OWNER", "account_state": "ACTIVE", "subscription": deepcopy(sub)}
        self.member = {**deepcopy(self.owner), "_id": "U2", "email": "member@example.com", "account_role": "MEMBER"}
        self.other = {**deepcopy(self.owner), "_id": "U3", "email": "other@example.com", "account_id": "ACC_two"}
        self.db["users"].docs = [deepcopy(self.owner), deepcopy(self.member), deepcopy(self.other)]
        self.account = {"_id": "ACC_one", "status": "ACTIVE", "setup_status": "COMPLETE", "name": "One", "owner_user_id": "U1", "billing_version": 1, "subscription": deepcopy(sub)}
        self.db["customer_accounts"].docs = [deepcopy(self.account), {**deepcopy(self.account), "_id": "ACC_two", "owner_user_id": "U3"}]
        self.db["projects"].docs = [{"project_id": "P1", "name": "Module", "account_id": "ACC_one", "created_by": self.member["email"]}, {"project_id": "P2", "name": "Other", "account_id": "ACC_two", "created_by": self.other["email"]}]
        self.db["project_memberships"].docs = [{"project_id": "P1", "email": self.member["email"], "role": "ADMIN", "status": "ACTIVE"}]

    def client(self, user):
        app = FastAPI()
        for router in (account_routes.router, project_team_routes.router, subscription_routes.router): app.include_router(router)
        @app.get("/content/{project_id}")
        async def content(project_id: str, current=Depends(auth_dependency.get_current_user)): return {"visible": True}
        p = patch.object(auth_dependency, "decode_token", return_value={"email": user["email"]}); p.start(); self.addCleanup(p.stop)
        return TestClient(app, cookies={"access_token": "synthetic"})

    async def test_shared_subscription_and_mutations_never_touch_legacy_user_counters(self):
        before = deepcopy(self.db["users"].docs)
        await subscription_services.increment_usage("member@example.com", "stories_used")
        self.assertEqual((await subscription_services.get_subscription("owner@example.com"))["usage"]["stories_used"], 1)
        self.assertEqual((await subscription_services.get_subscription("other@example.com"))["usage"]["stories_used"], 0)
        self.assertEqual((await sync_usage.sync_usage("member@example.com"))["stories_used"], 1)
        await subscription_services.decrement_usage("owner@example.com", "stories_used")
        await subscription_services.decrement_usage("owner@example.com", "stories_used")
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["stories_used"], 0)
        self.assertEqual(before, self.db["users"].docs)

    async def test_cutover_has_no_silent_user_fallback_even_after_flag_off(self):
        settings.features.account_subscriptions = False
        self.assertEqual((await subscription_services.get_subscription("member@example.com"))["billing_scope"], "ACCOUNT")
        del self.db["customer_accounts"].docs[0]["billing_version"]
        settings.features.account_subscriptions = True
        with self.assertRaises(HTTPException): await subscription_services.get_subscription("member@example.com")

    async def test_account_owner_manages_project_without_content_membership_then_can_assign_self(self):
        client = self.client(self.owner)
        self.assertEqual(client.get('/content/P1').status_code, 404)
        self.assertEqual(client.get('/account/projects').json(), [{"project_id": "P1", "name": "Module"}])
        with patch.object(project_team_service, "get_next_sequence", return_value="MEM_new"):
            response = client.post('/projects/P1/team', json={"email": self.owner["email"], "role": "ADMIN"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(client.get('/content/P1').status_code, 200)
        self.assertEqual(client.get('/projects/P2/team').status_code, 404)
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["team_members_used"], 0)

    async def test_project_admin_and_platform_role_cannot_manage_account_assignments(self):
        self.db["users"].docs[1]["platform_role"] = "OWNER"
        client = self.client(self.member)
        self.assertEqual(client.post('/projects/P1/team', json={"email": self.owner["email"], "role": "ADMIN"}).status_code, 403)
        self.assertEqual(client.get('/account/projects').status_code, 403)
        self.assertEqual(client.patch('/auth/auth/upgrade-plan?plan=enterprise').status_code, 403)
        self.assertEqual(client.get('/account/subscription').json()["billing_scope"], "ACCOUNT")

    async def test_seats_are_atomic_and_revoke_releases_without_project_assignment_charges(self):
        self.db["customer_accounts"].docs[0]["subscription"]["limits"]["team_members_limit"] = 1
        service = CustomerAccounts(self.db)
        outcomes = await asyncio.gather(service.invite(dict(self.owner), "new1@example.com", "MEMBER"), service.invite(dict(self.owner), "new2@example.com", "MEMBER"), return_exceptions=True)
        self.assertEqual(sum(isinstance(outcome, dict) for outcome in outcomes), 1)
        invite = next(outcome for outcome in outcomes if isinstance(outcome, dict))
        await service.revoke(dict(self.owner), invite["invitation_id"])
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["team_members_used"], 0)

    async def test_invitation_acceptance_does_not_charge_second_seat(self):
        service = CustomerAccounts(self.db)
        invite = await service.invite(dict(self.owner), "new@example.com", "MEMBER")
        await service.register({"email": "new@example.com"}, invite["token"])
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["team_members_used"], 1)

    async def test_ai_last_credit_is_shared_across_users_and_projects(self):
        self.db["projects"].docs.append({"project_id": "P3", "account_id": "ACC_one", "created_by": self.owner["email"]})
        service = AIUsageService(database=self.db, redis_backend=LocalCache(), gateway=Gateway(), now=lambda: self.now)
        outcomes = await asyncio.gather(service.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic")), service.execute(AIOperation.TEST_DESIGN, "P3", dict(self.owner), LLMRequest(prompt="synthetic")), return_exceptions=True)
        self.assertEqual(sum(isinstance(outcome, LLMResponse) for outcome in outcomes), 1)
        self.assertEqual(sum(isinstance(outcome, AIUsageError) for outcome in outcomes), 1)
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["ai_gen_used"], 1)
        self.assertEqual(self.db["ai_usage_records"].docs[0]["account_id"], "ACC_one")

    async def test_account_ai_failure_refunds_authentication_error_but_counts_timeout(self):
        for code, expected in (("AUTHENTICATION_ERROR", 0), ("TIMEOUT", 1)):
            gateway = Gateway(error=LLMProviderError(code, "synthetic"))
            service = AIUsageService(database=self.db, redis_backend=LocalCache(), gateway=gateway, now=lambda: self.now)
            with self.assertRaises(LLMProviderError):
                await service.execute(AIOperation.TEST_DESIGN, "P1", dict(self.member), LLMRequest(prompt="synthetic"))
            self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["ai_gen_used"], expected)

    async def test_legacy_scenario_generation_uses_shared_ai_boundary_once_for_multiple_results(self):
        from app.services.ai.scenario_generator import generate_scenarios_from_prompt
        response = LLMResponse('[{"title":"One"},{"title":"Two"}]', "openai", "synthetic")
        with patch.object(AIUsageService, "execute", new=AsyncMock(return_value=response)) as invoke:
            scenarios = await generate_scenarios_from_prompt("P1", "synthetic", user=self.member)
        self.assertEqual(len(scenarios), 2)
        invoke.assert_awaited_once()
        self.assertEqual(invoke.await_args.args[0], AIOperation.SCENARIO_DESIGN)
        self.assertEqual(invoke.await_args.args[2], self.member)

    async def test_plan_change_preserves_usage_and_billing_period(self):
        self.db["customer_accounts"].docs[0]["subscription"]["usage"]["stories_used"] = 7
        before = deepcopy(self.db["customer_accounts"].docs[0]["subscription"])
        await subscription_services.upgrade_plan(self.owner["email"], "pro")
        changed = self.db["customer_accounts"].docs[0]["subscription"]
        self.assertEqual(changed["plan"], "pro")
        self.assertEqual(changed["usage"], before["usage"])
        self.assertEqual(changed["ai_usage_period_start"], before["ai_usage_period_start"])

    async def test_migration_preserves_counters_plan_and_is_repeatable(self):
        account = deepcopy(self.account); account.pop("billing_version"); account.pop("subscription")
        self.db["customer_accounts"].docs[0] = account
        self.db["users"].docs[0]["subscription"]["usage"]["stories_used"] = 4
        self.db["users"].docs[1]["subscription"]["usage"]["stories_used"] = 3
        users = self.db["users"].docs[:2]; before = deepcopy(users)
        plan = plan_subscriptions([account], users, self.db["projects"].docs, {"ACC_one": {"stories_used": 5}}, [], now=self.now)
        self.assertEqual(plan["errors"], [])
        self.assertEqual(plan["changes"][0]["subscription"]["usage"]["stories_used"], 7)
        self.assertEqual(plan["changes"][0]["subscription"]["usage"]["team_members_used"], 1)
        with self.assertRaises(ValueError): await apply_subscriptions(self.db, plan, plan["plan_digest"])
        with self.assertRaises(ValueError): await apply_subscriptions(self.db, plan, "stale", maintenance_confirmed=True)
        await apply_subscriptions(self.db, plan, plan["plan_digest"], maintenance_confirmed=True)
        repeat = plan_subscriptions(self.db["customer_accounts"].docs[:1], users, [], {}, [], now=self.now)
        self.assertEqual(repeat["changes"], [])
        self.assertEqual(before, users)

    async def test_migration_requires_paid_plan_conflict_review_and_stale_account_stops(self):
        account = deepcopy(self.account); account.pop("billing_version"); account.pop("subscription")
        users = deepcopy(self.db["users"].docs[:2]); users[1]["subscription"]["plan"] = "pro"
        plan = plan_subscriptions([account], users, [], {}, [], now=self.now)
        self.assertTrue(plan["errors"])
        plan = plan_subscriptions([account], users, [], {}, [], {"subscription_sources": {"ACC_one": "U2"}}, now=self.now)
        self.assertEqual(plan["errors"], [])
        with self.assertRaises(ValueError): await apply_subscriptions(self.db, plan, plan["plan_digest"], maintenance_confirmed=True)


if __name__ == "__main__": unittest.main()
