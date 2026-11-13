"""Synthetic account integration: ASGI/auth/provider/Mongo doubles, no real services."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "account_tests", "REDIS_HOST": "localhost", "REDIS_PORT": "6399", "REDIS_USERNAME": "", "REDIS_PASSWORD": "", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from bson import ObjectId
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from pymongo.errors import DuplicateKeyError
    from app.config import settings, FeatureFlags
    from app.services.customer_accounts import CustomerAccounts, now
    from app.services.account_migration import plan_accounts, apply_accounts
    from app.routes import account_routes, auth_routes, project_routes
    from app.models.user_model import User
    from app.models.project_model import ProjectCreate
    from app.services import project_team_service
    from app.utils import project_authorization, auth_dependency


def matches(doc, query):
    for key, expected in query.items():
        value = doc.get(key)
        if isinstance(expected, dict):
            if "$gt" in expected:
                target = expected["$gt"]
                if isinstance(value, datetime) and isinstance(target, datetime):
                    value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
                    target = target.replace(tzinfo=timezone.utc) if target.tzinfo is None else target
                if value is None or not value > target: return False
            if "$in" in expected and value not in expected["$in"]: return False
        elif value != expected: return False
    return True


class Cursor:
    def __init__(self, docs): self.docs = deepcopy(docs)
    async def to_list(self, limit): return self.docs[:limit] if limit else self.docs
    def __aiter__(self): self.items = iter(self.docs); return self
    async def __anext__(self):
        try: return next(self.items)
        except StopIteration: raise StopAsyncIteration


class Collection:
    def __init__(self): self.docs = []
    async def find_one(self, query, *args, **kwargs): return deepcopy(next((doc for doc in self.docs if matches(doc, query)), None))
    def find(self, query, *args): return Cursor([doc for doc in self.docs if matches(doc, query)])
    async def insert_one(self, doc):
        if any((doc.get("_id") is not None and row.get("_id") == doc["_id"]) or ("email" in doc and row.get("email") == doc["email"]) for row in self.docs): raise DuplicateKeyError("synthetic")
        self.docs.append(deepcopy(doc)); return SimpleNamespace(inserted_id=doc.get("_id", ObjectId()))
    async def update_one(self, query, update, upsert=False):
        row = next((doc for doc in self.docs if matches(doc, query)), None)
        if row is None and upsert:
            row = {**query, **update.get("$setOnInsert", {})}; self.docs.append(row)
        if row is None: return SimpleNamespace(matched_count=0, modified_count=0)
        row.update(deepcopy(update.get("$set", {})))
        return SimpleNamespace(matched_count=1, modified_count=1)
    async def find_one_and_update(self, query, update, **kwargs):
        old = await self.find_one(query)
        if old is None: return None
        await self.update_one(query, update)
        return await self.find_one({"_id": old["_id"]})
    async def delete_one(self, query):
        old = next((row for row in self.docs if matches(row, query)), None)
        if old is not None: self.docs.remove(old)
        return SimpleNamespace(deleted_count=int(old is not None))


class DB(dict):
    def __missing__(self, key): self[key] = Collection(); return self[key]


class AccountsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = DB(); self.service = CustomerAccounts(self.db)
        for target, key, value in [(settings, "features", FeatureFlags(customer_accounts=True)), (account_routes, "db", self.db),
            (auth_routes, "db", self.db), (project_routes, "db", self.db), (project_authorization, "db", self.db),
            (auth_dependency, "db", self.db), (project_team_service, "db", self.db)]:
            p = patch.object(target, key, value); p.start(); self.addCleanup(p.stop)

    async def owner(self, email="owner@example.com"):
        return await self.service.register({"email": email, "name": "Customer", "role": "admin", "password": "hash", "platform_role": "NONE", "subscription": {"sentinel": "unchanged"}})

    def client(self, user):
        app = FastAPI(); app.include_router(account_routes.router)
        app.dependency_overrides[account_routes.get_current_user] = lambda: dict(user)
        return TestClient(app)

    async def test_signup_ignores_client_account_assignment_and_returns_safe_identity(self):
        payload = User(name="Customer", email="new@example.com", password="synthetic", account_id="FORGED", account_role="OWNER")
        with patch.object(auth_routes.pwd_context, "hash", return_value="hash"), patch.object(auth_routes, "store_refresh_token"), patch.object(auth_routes, "ensure_platform_owner", AsyncMock()):
            response = await auth_routes.signup(payload)
        body = __import__('json').loads(response.body)
        self.assertNotEqual(body["user"]["account_id"], "FORGED")
        self.assertEqual(body["user"]["account_role"], "OWNER")
        self.assertNotIn("password", body["user"])
        self.assertNotIn("invitation_token", body["user"])
        self.assertEqual(self.db["customer_accounts"].docs[0]["setup_status"], "PENDING")

    async def test_name_is_in_onboarding_and_project_creation_uses_authoritative_account(self):
        owner = await self.owner(); client = self.client(owner)
        self.assertEqual(client.patch('/account', json={"name": "Customer One"}).status_code, 200)
        self.assertEqual(client.get('/account').json()["name"], "Customer One")
        with patch.object(project_routes, "get_next_sequence", AsyncMock(return_value="PRJ020")), patch.object(project_routes, "create_creator_membership", AsyncMock()):
            result = await project_routes.create_project(ProjectCreate(name="Module", created_by="forged@example.com"), dict(owner), None)
        self.assertEqual(result.account_id, owner["account_id"])
        self.assertEqual(result.created_by, owner["email"])

    async def test_account_display_numbers_are_separate_from_route_ids(self):
        owner = await self.owner()
        await self.service.name(owner, "Customer One")
        counters = {}
        async def sequence(key, prefix):
            counters[key] = counters.get(key, 0) + 1
            return f"{prefix}{counters[key]:03d}"
        with patch.object(project_routes, "get_next_sequence", side_effect=sequence), patch.object(project_routes, "create_creator_membership", AsyncMock()):
            first = await project_routes.create_project(ProjectCreate(name="First", created_by=owner["email"]), dict(owner), None)
            second = await project_routes.create_project(ProjectCreate(name="Second", created_by=owner["email"]), dict(owner), None)
            other = await self.owner("second@example.com")
            await self.service.name(other, "Customer Two")
            third = await project_routes.create_project(ProjectCreate(name="Third", created_by=other["email"]), dict(other), None)
        self.assertEqual([first.project_id, second.project_id, third.project_id], ["PRJ001", "PRJ002", "PRJ003"])
        self.assertEqual([first.display_id, second.display_id, third.display_id], ["PRJ001", "PRJ002", "PRJ001"])

    async def test_deleting_last_project_preserves_onboarding_and_clears_context(self):
        project = {"project_id": "PRJ020", "created_by": "owner@example.com"}
        collections = {name: SimpleNamespace(delete_one=AsyncMock(return_value=SimpleNamespace(deleted_count=1)),
            delete_many=AsyncMock(), count_documents=AsyncMock(return_value=0),
            update_one=AsyncMock(), update_many=AsyncMock())
            for name in ("projects", "project_memberships", "ai_configurations", "encrypted_secrets", "users")}
        with patch.object(project_routes, "db", collections), patch.object(project_routes, "require_project_admin", AsyncMock(return_value=(project, {}))), patch("app.services.account_billing.billing_account", AsyncMock(return_value=None)):
            await project_routes.delete_project("PRJ020", {"email": "owner@example.com"})
        query, update = collections["users"].update_many.call_args.args
        self.assertEqual(query, {"onboarding.context.project_id": "PRJ020"})
        self.assertIsNone(update["$set"]["onboarding.context.project_id"])
        self.assertEqual(update["$set"]["onboarding.onboarding_status"], "completed")
        for call in collections["users"].update_one.call_args_list:
            self.assertNotIn("onboarding.onboarding_status", call.args[1].get("$set", {}))

    async def test_pending_account_cannot_create_project(self):
        owner = await self.owner()
        with self.assertRaises(HTTPException) as error:
            await project_routes.create_project(ProjectCreate(name="Module", created_by=owner["email"]), owner, None)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.db["projects"].docs, [])

    async def test_wrong_invite_token_rejected_and_valid_invite_joins_existing_account(self):
        owner = await self.owner(); invite = await self.service.invite(owner, "member@example.com", "MEMBER")
        with self.assertRaises(HTTPException): await self.service.register({"email": "member@example.com"}, "wrong")
        member = await self.service.register({"email": "member@example.com"}, invite["token"])
        self.assertEqual(member["account_id"], owner["account_id"])
        self.assertEqual(member["account_role"], "MEMBER")
        self.assertEqual(member["onboarding"]["onboarding_status"], "completed")
        self.assertEqual(len(self.db["customer_accounts"].docs), 1)
        self.assertNotIn(invite["token"], str(self.db["account_invitations"].docs))
        self.assertEqual(self.db["account_invitations"].docs[0]["status"], "ACCEPTED")

    async def test_verified_provider_email_may_accept_invite_but_unverified_email_cannot(self):
        owner = await self.owner(); await self.service.invite(owner, "google@example.com", "MEMBER")
        with self.assertRaises(HTTPException): await self.service.register({"email": "google@example.com"}, verified_email=False)
        member = await self.service.register({"email": "google@example.com"}, verified_email=True)
        self.assertEqual(member["account_id"], owner["account_id"])

    async def test_bson_naive_utc_invitation_expiry_is_supported(self):
        owner = await self.owner()
        invite = await self.service.invite(owner, "bson@example.com", "MEMBER")
        self.db["account_invitations"].docs[0]["expires_at"] = (now() + timedelta(days=1)).replace(tzinfo=None)
        member = await self.service.register({"email": "bson@example.com"}, invite["token"])
        self.assertEqual(member["account_id"], owner["account_id"])

    async def test_claimed_invitation_without_user_cannot_provision_another_account(self):
        owner = await self.owner()
        await self.service.invite(owner, "claimed@example.com", "MEMBER")
        self.db["account_invitations"].docs[0]["status"] = "CLAIMED"
        with self.assertRaises(HTTPException) as error:
            await self.service.register({"email": "claimed@example.com"}, verified_email=True)
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(self.db["customer_accounts"].docs), 1)
        self.assertEqual(len(self.db["users"].docs), 1)

    async def test_revoked_expired_and_replayed_invites_do_not_create_users(self):
        owner = await self.owner(); invite = await self.service.invite(owner, "revoke@example.com", "MEMBER")
        await self.service.revoke(owner, invite["invitation_id"])
        with self.assertRaises(HTTPException): await self.service.register({"email": "revoke@example.com"}, invite["token"])
        invite = await self.service.invite(owner, "expire@example.com", "MEMBER")
        self.db["account_invitations"].docs[0]["expires_at"] = now() - timedelta(seconds=1)
        with self.assertRaises(HTTPException): await self.service.register({"email": "expire@example.com"}, invite["token"])
        self.assertEqual(len(self.db["users"].docs), 1)

    async def test_one_pending_account_invitation_per_identity(self):
        one, two = await self.owner(), await self.owner("two@example.com")
        results = await asyncio.gather(self.service.invite(one, "new@example.com", "MEMBER"), self.service.invite(two, "new@example.com", "MEMBER"), return_exceptions=True)
        self.assertEqual(sum(isinstance(result, HTTPException) for result in results), 1)
        self.assertEqual(len(self.db["account_invitations"].docs), 1)

    async def test_role_claims_cannot_grant_account_admin_and_lists_do_not_leak_invite_token(self):
        owner = await self.owner(); invite = await self.service.invite(owner, "member@example.com", "MEMBER")
        member = await self.service.register({"email": "member@example.com"}, invite["token"])
        forged = {**member, "account_role": "OWNER", "platform_role": "OWNER"}
        client = self.client(forged)
        self.assertEqual(client.patch('/account', json={"name": "Bad rename"}).status_code, 403)
        self.assertEqual(client.post('/account/invitations', json={"email": "new@example.com"}).status_code, 403)
        self.assertEqual(client.get('/account/invitations').status_code, 403)
        second = self.client(owner).post('/account/invitations', json={"email": "other@example.com"})
        self.assertEqual(second.status_code, 201)
        listing = self.client(owner).get('/account/invitations')
        self.assertNotIn(second.json()["token"], listing.text); self.assertNotIn("token_digest", listing.text)

    async def test_cross_account_stale_project_membership_and_platform_owner_do_not_bypass(self):
        owner, other = await self.owner(), await self.owner("other@example.com")
        self.db["projects"].docs.append({"project_id": "P1", "account_id": owner["account_id"], "created_by": owner["email"]})
        self.db["project_memberships"].docs.append({"project_id": "P1", "email": other["email"], "status": "ACTIVE", "role": "ADMIN"})
        other["platform_role"] = "OWNER"
        for flag in (True, False):
            settings.features.customer_accounts = flag
            with self.assertRaises(HTTPException) as error: await project_authorization.require_project_member("P1", dict(other))
            self.assertEqual(error.exception.status_code, 404)

    async def test_account_admin_can_add_only_same_account_existing_member(self):
        owner, other = await self.owner(), await self.owner("other@example.com")
        invite = await self.service.invite(owner, "member@example.com", "MEMBER")
        member = await self.service.register({"email": "member@example.com"}, invite["token"])
        project = {"project_id": "P1", "account_id": owner["account_id"], "created_by": owner["email"]}
        self.db["projects"].docs.append(project)
        with patch.object(project_team_service, "require_project_admin", AsyncMock(return_value=(project, {}))), patch.object(project_team_service, "get_subscription", AsyncMock(return_value={"usage": {}, "limits": {"team_members_limit": 5}})), patch.object(project_team_service, "increment_usage", AsyncMock()), patch.object(project_team_service, "get_next_sequence", AsyncMock(return_value="MEM1")):
            for email in (other["email"], "new@example.com"):
                with self.assertRaises(HTTPException): await project_team_service.invite_member("P1", email, "TESTER", dict(owner))
            result = await project_team_service.invite_member("P1", member["email"], "TESTER", dict(owner))
            self.assertEqual(result["status"], "ACTIVE")

    async def test_login_does_not_create_accounts_and_unmapped_users_fail_closed(self):
        owner = await self.owner()
        with patch.object(auth_routes.pwd_context, "verify", return_value=True), patch.object(auth_routes, "store_refresh_token"), patch.object(auth_routes, "ensure_platform_owner", AsyncMock()):
            await auth_routes.login({"email": owner["email"], "password": "synthetic"})
            await auth_routes.login({"email": owner["email"], "password": "synthetic"})
            self.assertEqual(len(self.db["customer_accounts"].docs), 1)
            self.db["users"].docs.append({"email": "legacy@example.com", "password": "hash"})
            with self.assertRaises(HTTPException): await auth_routes.login({"email": "legacy@example.com", "password": "synthetic"})
            self.assertEqual(len(self.db["customer_accounts"].docs), 1)

    async def test_suspended_and_partial_accounts_cannot_authenticate(self):
        owner = await self.owner(); self.db["customer_accounts"].docs[0]["status"] = "SUSPENDED"
        with self.assertRaises(HTTPException): await self.service.require(owner)
        self.db["customer_accounts"].docs[0]["status"] = "ACTIVE"
        self.db["users"].docs[0]["account_state"] = "PROVISIONING"
        with self.assertRaises(HTTPException): await self.service.require(owner)

    async def test_disabled_routes_reject_and_keep_subscription_untouched(self):
        owner = await self.owner(); settings.features.customer_accounts = False
        response = self.client(owner).post('/account/invitations', json={"email": "new@example.com"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db["account_invitations"].docs, [])
        self.assertEqual(self.db["users"].docs[0]["subscription"], {"sentinel": "unchanged"})

    async def test_actual_auth_dependency_rejects_path_query_body_and_resource_references(self):
        owner, other = await self.owner(), await self.owner("other@example.com")
        for key, actor in (("P1", owner), ("P2", other)):
            self.db["projects"].docs.append({"project_id": key, "account_id": actor["account_id"], "created_by": actor["email"]})
            self.db["project_memberships"].docs.append({"project_id": key, "email": owner["email"], "status": "ACTIVE", "role": "ADMIN"})
        self.db["testcases"].docs.append({"testcase_id": "TC2", "project_id": "P2"})
        app = FastAPI()
        @app.post('/probe/{project_id}')
        async def endpoint(project_id: str, payload: dict, user=__import__('fastapi').Depends(auth_dependency.get_current_user)):
            return {"ok": True}
        @app.post('/resource')
        async def resource(payload: dict, user=__import__('fastapi').Depends(auth_dependency.get_current_user)):
            return {"ok": True}
        client = TestClient(app); client.cookies.set("access_token", "auth-double")
        with patch.object(auth_dependency, "decode_token", return_value={"email": owner["email"]}):
            self.assertEqual(client.post('/probe/P1', json={}).status_code, 200)
            self.assertEqual(client.post('/probe/P2', json={}).status_code, 404)
            self.assertEqual(client.post('/resource?project_id=P2', json={}).status_code, 404)
            self.assertEqual(client.post('/resource', json={"project_id": "P2"}).status_code, 404)
            self.assertEqual(client.post('/resource', json={"testcase_id": "TC2"}).status_code, 404)
            self.assertEqual(client.post('/resource', json={"testcase_ids": ["TC2"]}).status_code, 404)
            self.assertEqual(client.post('/probe/P1', json={"project_id": "P2"}).status_code, 422)

    async def test_real_google_callback_path_joins_invited_account_and_rejects_unverified_identity(self):
        owner = await self.owner(); await self.service.invite(owner, "google@example.com", "MEMBER")
        from starlette.requests import Request
        request = Request({"type": "http", "method": "GET", "path": "/auth/google/callback", "headers": []})
        info = {"email": "google@example.com", "name": "Google member", "sub": "synthetic-google", "email_verified": False}
        client = SimpleNamespace(authorize_access_token=AsyncMock(return_value={"userinfo": info}))
        with patch.object(auth_routes.oauth, "create_client", return_value=client), patch.object(auth_routes, "store_refresh_token"), patch.object(auth_routes, "ensure_platform_owner", AsyncMock()), patch.object(auth_routes, "activate_pending_memberships", AsyncMock()), patch.object(settings, "frontend_url", "http://localhost:3000"):
            with self.assertRaises(HTTPException) as error: await auth_routes.oauth_callback(request, "google")
            self.assertEqual(error.exception.status_code, 400)
            info["email_verified"] = True
            response = await auth_routes.oauth_callback(request, "google")
            self.assertEqual(response.status_code, 307)
            await auth_routes.oauth_callback(request, "google")
        member = await self.db["users"].find_one({"email": "google@example.com"})
        self.assertEqual(member["account_id"], owner["account_id"])
        self.assertEqual(len(self.db["customer_accounts"].docs), 1)

    async def test_github_callback_uses_verified_primary_email_not_public_profile_email(self):
        owner = await self.owner()
        await self.service.invite(owner, "github@example.com", "MEMBER")
        from starlette.requests import Request
        request = Request({"type": "http", "method": "GET", "path": "/auth/github/callback", "headers": []})
        primary = {"email": "github@example.com", "primary": True, "verified": False}
        async def get(path, **kwargs):
            data = {"email": "untrusted@example.com", "login": "fixture", "id": 123} if path == "user" else [primary]
            return SimpleNamespace(json=lambda: data)
        client = SimpleNamespace(authorize_access_token=AsyncMock(return_value={}), get=get)
        with patch.object(auth_routes.oauth, "create_client", return_value=client), patch.object(auth_routes, "store_refresh_token"), patch.object(auth_routes, "ensure_platform_owner", AsyncMock()), patch.object(settings, "frontend_url", "http://localhost:3000"):
            with self.assertRaises(HTTPException) as error:
                await auth_routes.oauth_callback(request, "github")
            self.assertEqual(error.exception.status_code, 400)
            primary["verified"] = True
            self.assertEqual((await auth_routes.oauth_callback(request, "github")).status_code, 307)
        member = await self.db["users"].find_one({"email": "github@example.com"})
        self.assertEqual(member["account_id"], owner["account_id"])
        self.assertIsNone(await self.db["users"].find_one({"email": "untrusted@example.com"}))

    async def test_interrupted_signup_is_not_silently_reprovisioned_by_login(self):
        with patch.object(self.db["customer_accounts"], "insert_one", AsyncMock(side_effect=RuntimeError("synthetic storage interruption"))):
            with self.assertRaises(RuntimeError): await self.owner()
        self.assertEqual(self.db["users"].docs[0]["account_state"], "PROVISIONING")
        with patch.object(auth_routes.pwd_context, "verify", return_value=True):
            with self.assertRaises(HTTPException): await auth_routes.login({"email": "owner@example.com", "password": "synthetic"})
        self.assertEqual(self.db["customer_accounts"].docs, [])


class MigrationTests(unittest.IsolatedAsyncioTestCase):
    def sample(self):
        users = [{"_id": "U1", "email": "one@example.com"}, {"_id": "U2", "email": "two@example.com"}]
        projects = [{"project_id": "P1", "created_by": "one@example.com"}]
        mapping = {"accounts": [{"account_id": "ACC_one", "name": "Customer One", "users": [{"user_id": "U1", "role": "OWNER"}, {"user_id": "U2", "role": "MEMBER"}]}]}
        return users, projects, mapping

    async def test_dry_run_is_read_only_apply_is_explicit_and_repeatable(self):
        users, projects, mapping = self.sample(); db = DB(); db["users"].docs = deepcopy(users); db["projects"].docs = deepcopy(projects)
        plan = plan_accounts(users, projects, [], mapping)
        self.assertEqual(db["customer_accounts"].docs, [])
        with self.assertRaises(ValueError): await apply_accounts(db, plan, plan["plan_digest"])
        with self.assertRaises(ValueError): await apply_accounts(db, plan, "wrong", maintenance_confirmed=True)
        await apply_accounts(db, plan, plan["plan_digest"], maintenance_confirmed=True)
        repeat = plan_accounts(db["users"].docs, db["projects"].docs, [], mapping, db["customer_accounts"].docs)
        self.assertEqual(repeat["errors"], []); self.assertEqual(repeat["changes"], [])
        await apply_accounts(db, repeat, repeat["plan_digest"], maintenance_confirmed=True)
        self.assertEqual(len(db["customer_accounts"].docs), 1)

    async def test_conflicts_block_automatic_customer_mergers_and_reparenting(self):
        users, projects, mapping = self.sample()
        mapping["accounts"][0]["users"].pop()
        mapping["accounts"].append({"account_id": "ACC_two", "name": "Customer Two", "users": [{"user_id": "U2", "role": "OWNER"}]})
        membership = {"membership_id": "M1", "project_id": "P1", "email": "two@example.com", "status": "ACTIVE"}
        plan = plan_accounts(users, projects, [membership], mapping)
        self.assertTrue(any("Cross-account" in item for item in plan["errors"]))
        users[0]["account_id"] = "ACC_existing"
        self.assertTrue(any("Reparenting" in item for item in plan_accounts(users, projects, [], mapping)["errors"]))

    async def test_omitted_account_id_is_stable_and_preserves_assigned_owner(self):
        users, projects, mapping = self.sample()
        del mapping["accounts"][0]["account_id"]
        original = deepcopy(mapping)
        plan = plan_accounts(users, projects, [], mapping)
        self.assertEqual(plan["errors"], [])
        account_id = plan["accounts"][0]["_id"]
        self.assertTrue(account_id.startswith("ACC_"))
        self.assertEqual(mapping, original)
        self.assertEqual(plan, plan_accounts(users, projects, [], mapping))
        mapping["accounts"][0]["name"] = "Renamed Customer"
        self.assertEqual(plan_accounts(users, projects, [], mapping)["accounts"][0]["_id"], account_id)
        db = DB(); db["users"].docs = deepcopy(users); db["projects"].docs = deepcopy(projects)
        await apply_accounts(db, plan, plan["plan_digest"], maintenance_confirmed=True)
        repeat = plan_accounts(db["users"].docs, db["projects"].docs, [], original, db["customer_accounts"].docs)
        self.assertEqual(repeat["changes"], [])
        self.assertEqual(repeat["accounts"][0]["_id"], account_id)
        users[0]["account_id"] = "ACC_preexisting"
        retained = plan_accounts(users, projects, [], original)
        self.assertEqual(retained["accounts"][0]["_id"], "ACC_preexisting")

    async def test_omitted_id_requires_valid_owner_and_never_merges_foreign_members(self):
        users, projects, mapping = self.sample()
        del mapping["accounts"][0]["account_id"]
        mapping["accounts"][0]["users"][0]["role"] = "MEMBER"
        self.assertTrue(plan_accounts(users, projects, [], mapping)["errors"])
        mapping["accounts"][0]["users"][0]["role"] = "OWNER"
        users[1]["account_id"] = "ACC_foreign"
        self.assertTrue(any("Reparenting" in error for error in plan_accounts(users, projects, [], mapping)["errors"]))

    async def test_unknown_legacy_invites_are_quarantined_and_duplicate_identities_block(self):
        users, projects, mapping = self.sample()
        membership = {"membership_id": "M1", "project_id": "P1", "email": "unknown@example.com", "status": "INVITED"}
        plan = plan_accounts(users, projects, [membership], mapping)
        self.assertEqual(plan["errors"], [])
        self.assertEqual(plan["changes"][-1]["set"]["status"], "LEGACY_REVIEW_REQUIRED")
        users.append({"_id": "U3", "email": "one@example.com"})
        self.assertTrue(plan_accounts(users, projects, [], mapping)["errors"])

    async def test_explicit_legacy_project_claim_recovers_owner_and_preserves_history(self):
        users, projects, mapping = self.sample()
        projects[0]["created_by"] = "deleted-owner@example.com"
        mapping["accounts"][0]["legacy_project_ids"] = ["P1"]
        membership = {"membership_id": "M1", "project_id": "P1", "email": "deleted-owner@example.com", "status": "ACTIVE"}
        db = DB(); db["users"].docs = deepcopy(users); db["projects"].docs = deepcopy(projects)
        db["project_memberships"].docs = [deepcopy(membership)]
        plan = plan_accounts(users, projects, [membership], mapping)
        self.assertEqual(plan["errors"], [])
        await apply_accounts(db, plan, plan["plan_digest"], maintenance_confirmed=True)
        project = db["projects"].docs[0]
        self.assertEqual(project["created_by"], "one@example.com")
        self.assertEqual(project["legacy_created_by"], "deleted-owner@example.com")
        self.assertEqual(db["project_memberships"].docs[0]["status"], "LEGACY_REVIEW_REQUIRED")
        self.assertEqual(db["project_memberships"].docs[0]["legacy_status"], "ACTIVE")
        self.assertEqual(set(change["collection"] for change in plan["changes"]), {"users", "projects", "project_memberships"})
        repeat = plan_accounts(db["users"].docs, db["projects"].docs, db["project_memberships"].docs, mapping, db["customer_accounts"].docs)
        self.assertEqual(repeat["errors"], []); self.assertEqual(repeat["changes"], [])

    async def test_legacy_claims_reject_unknown_duplicate_foreign_and_missing_projects(self):
        users, projects, mapping = self.sample()
        mapping["accounts"][0]["legacy_project_ids"] = ["UNKNOWN", "P1", "P1"]
        errors = plan_accounts(users, projects, [], mapping)["errors"]
        self.assertTrue(any("Unknown legacy" in error for error in errors))
        self.assertTrue(any("Multiply claimed" in error for error in errors))
        mapping["accounts"][0]["legacy_project_ids"] = ["P1"]
        projects[0]["account_id"] = "ACC_foreign"
        self.assertTrue(any("Reparenting" in error for error in plan_accounts(users, projects, [], mapping)["errors"]))
        orphan = {"membership_id": "ORPHAN", "project_id": "MISSING", "email": "one@example.com", "status": "ACTIVE"}
        self.assertTrue(any("Orphan" in error for error in plan_accounts(users, projects, [orphan], mapping)["errors"]))

    async def test_explicit_legacy_claim_cannot_override_another_mapped_creator_account(self):
        users, projects, mapping = self.sample()
        mapping["accounts"][0]["users"].pop()
        mapping["accounts"].append({"account_id": "ACC_two", "name": "Customer Two", "users": [{"user_id": "U2", "role": "OWNER"}], "legacy_project_ids": ["P1"]})
        self.assertTrue(any("conflicts with mapped creator" in error for error in plan_accounts(users, projects, [], mapping)["errors"]))
