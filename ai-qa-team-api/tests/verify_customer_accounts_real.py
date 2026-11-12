"""Opt-in development-service fixture. Real Mongo/Redis, bcrypt, JWT and API handlers.

Uses dedicated prefixed collections and unique synthetic identities. No production,
provider calls, normal-user records, or customer-data migration. ASGI, not a browser.
"""
import asyncio
from contextlib import ExitStack
import json
from uuid import uuid4
from unittest.mock import patch

import httpx
from fastapi import FastAPI

from app.config import settings
from app.db.connection import db
from app.routes import auth_routes, account_routes, project_routes, project_team_routes
from app.services import project_team_service, subscription_services, story_service, sync_usage
from app.services.account_migration import plan_accounts, apply_accounts
from app.utils import auth_dependency, project_authorization, redis_client


class FixtureDB:
    def __init__(self, prefix): self.prefix = prefix; self.names = set()
    def __getitem__(self, key):
        name = self.prefix + key
        self.names.add(name)
        return db[name]


async def main():
    if settings.app_env.lower() not in {"development", "local", "test"}:
        raise RuntimeError("Development-only fixture refused this environment.")
    prefix = "customer_account_fixture_" + uuid4().hex + "_"
    database = FixtureDB(prefix); migration = FixtureDB(prefix + "migration_")
    emails = [uuid4().hex + suffix + "@example.com" for suffix in ("owner", "member", "other")]
    results, cleanup, redis_ready = {}, False, False
    password = "Synthetic-account-fixture-only-724!"
    try:
        await asyncio.wait_for(db.command("ping"), 15)
        await asyncio.wait_for(asyncio.to_thread(redis_client.redis_client.ping), 15)
        redis_ready = True
        await database["users"].create_index("email", unique=True)
        await database["project_memberships"].create_index([("project_id", 1), ("email", 1)], unique=True)
        with ExitStack() as stack:
            stack.enter_context(patch.object(settings.features, "customer_accounts", True))
            for module in (auth_routes, account_routes, project_routes, project_team_service, subscription_services,
                           story_service, sync_usage, auth_dependency, project_authorization):
                stack.enter_context(patch.object(module, "db", database))
            app = FastAPI()
            for router in (auth_routes.router, account_routes.router, project_routes.router, project_team_routes.router): app.include_router(router)
            def session(): return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost")
            async with session() as owner, session() as member, session() as other:
                response = await owner.post('/auth/signup', json={"name": "Fixture Customer", "email": emails[0], "password": password})
                assert response.status_code == 200, "owner signup"
                original_account = response.json()["user"]["account_id"]
                assert response.cookies.get("access_token"), "signup cookie"
                assert (await owner.patch('/account', json={"name": "Synthetic Customer One"})).status_code == 200
                response = await owner.post('/projects', json={"name": "Synthetic module", "created_by": emails[0]})
                assert response.status_code == 200, "project creation"
                project_id = response.json()["project_id"]
                results["signup_name_project"] = True
                assert (await owner.post('/auth/login', json={"email": emails[0], "password": password})).status_code == 200
                assert (await owner.get('/account')).json()["account_id"] == original_account
                assert await database["customer_accounts"].count_documents({}) == 1
                results["normal_login_no_new_account"] = True
                invite = await owner.post('/account/invitations', json={"email": emails[1]})
                assert invite.status_code == 201, "account invitation"
                token = invite.json()["token"]
                assert token not in str(await database["account_invitations"].find_one({"_id": emails[1]}))
                response = await member.post('/auth/signup', json={"name": "Fixture Member", "email": emails[1], "password": password, "invitation_token": token})
                assert response.status_code == 200, "invited signup"
                assert response.json()["user"]["account_id"] == original_account
                assert (await member.get('/projects')).json() == []
                assert (await member.get(f'/projects/{project_id}')).status_code == 404
                assert (await member.post('/account/invitations', json={"email": "unused@example.com"})).status_code == 403
                response = await owner.post(f'/projects/{project_id}/team', json={"email": emails[1], "role": "TESTER"})
                assert response.status_code == 200, "project membership"
                assert (await member.get(f'/projects/{project_id}')).status_code == 200
                results["invitation_and_separate_project_membership"] = True
                assert (await other.post('/auth/signup', json={"name": "Fixture Other", "email": emails[2], "password": password})).status_code == 200
                await database["project_memberships"].insert_one({"membership_id": "STALE", "project_id": project_id, "email": emails[2], "role": "ADMIN", "status": "ACTIVE"})
                assert (await other.get(f'/projects/{project_id}')).status_code == 404
                assert (await owner.post(f'/projects/{project_id}/team', json={"email": emails[2], "role": "TESTER"})).status_code == 409
                assert (await other.get('/projects')).json() == []
                results["cross_account_and_stale_membership_denial"] = True
                outcomes = await asyncio.gather(*[owner.post('/account/invitations', json={"email": "race-" + prefix + "@example.com"}) for _ in range(2)])
                assert sorted(response.status_code for response in outcomes) == [201, 409]
                results["mongo_invitation_contention"] = True
                token_before = owner.cookies.get("access_token")
                async with session() as fresh:
                    fresh.cookies.set("access_token", token_before)
                    assert (await fresh.get('/account')).json()["name"] == "Synthetic Customer One"
                results["persisted_account_read_new_session"] = True
        # Real CAS migration applied only to a second synthetic namespace.
        from bson import ObjectId
        identity = ObjectId()
        users = [{"_id": identity, "email": "migration-fixture@example.com"}]
        projects = [{"project_id": "MIG1", "created_by": users[0]["email"]}]
        await migration["users"].insert_many(users); await migration["projects"].insert_many(projects)
        mapping = {"accounts": [{"account_id": "ACC_fixture", "name": "Synthetic Migration", "users": [{"user_id": str(identity), "role": "OWNER"}]}]}
        plan = plan_accounts(users, projects, [], mapping)
        assert not plan["errors"]
        await apply_accounts(migration, plan, plan["plan_digest"], maintenance_confirmed=True)
        repeat = plan_accounts(await migration["users"].find({}).to_list(None), await migration["projects"].find({}).to_list(None), [], mapping, await migration["customer_accounts"].find({}).to_list(None))
        assert repeat["changes"] == [] and not repeat["errors"]
        results["real_fixture_migration_repeatable"] = True
    except Exception as error:
        results["failure_type"] = type(error).__name__
        if isinstance(error, AssertionError):
            import traceback
            results["assertion_line"] = traceback.extract_tb(error.__traceback__)[-1].lineno
        # No exception text: database/provider diagnostics can include connection details.
    finally:
        try:
            for collection in database.names | migration.names:
                assert collection.startswith(prefix)
                await asyncio.wait_for(db[collection].drop(), 15)
            if redis_ready:
                for email in emails:
                    await asyncio.to_thread(redis_client.delete_refresh_token, email)
            cleanup = True
        except Exception:
            cleanup = False
        print(json.dumps({"real_development_services": results, "fixture_cleanup": cleanup}, indent=2))
    if "failure_type" in results or not cleanup: raise SystemExit(1)


if __name__ == "__main__": asyncio.run(main())
