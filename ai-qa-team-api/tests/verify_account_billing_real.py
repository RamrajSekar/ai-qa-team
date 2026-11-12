"""Opt-in real development Mongo/Redis + ASGI auth; synthetic isolated collections.

No existing-account migration, external OAuth, AI provider or browser execution.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import json
from uuid import uuid4
from unittest.mock import patch
import httpx
from fastapi import FastAPI
from bson import ObjectId
from verify_customer_accounts_real import FixtureDB
from app.config import settings
from app.db.connection import db
from app.routes import auth_routes, account_routes, project_routes, project_team_routes, subscription_routes
from app.services import subscription_services, sync_usage, story_service, project_team_service
from app.services.ai.ai_usage_service import AIUsageService
from app.services.ai.ai_usage_policy import AIOperation, AIUsageError
from app.services.ai.base_provider import LLMRequest, LLMResponse
from app.services.ai.llm_gateway import ResolvedLLMContext
from app.services.account_subscription_migration import plan_subscriptions, apply_subscriptions
from app.utils import auth_dependency, project_authorization, redis_client


class SyntheticGateway:
    async def resolve(self, project_id, request): return ResolvedLLMContext("MANAGED", "openai", "synthetic-no-provider", None)
    async def generate_resolved(self, context, request): return LLMResponse("synthetic", "openai", "synthetic-no-provider")


async def main():
    if settings.app_env.lower() not in {"development", "test", "local"}:
        raise SystemExit("Development-only fixture refused this environment.")
    prefix = "account_billing_fixture_" + uuid4().hex + "_"
    database = FixtureDB(prefix)
    emails = [uuid4().hex + suffix + "@example.com" for suffix in ("owner", "member", "other")]
    results = {}; cleanup = False; stage = "service_readiness"; redis_ready = False; redis_keys = []
    try:
        await asyncio.wait_for(db.command("ping"), 15)
        await asyncio.wait_for(asyncio.to_thread(redis_client.redis_client.ping), 15); redis_ready = True
        await database["users"].create_index("email", unique=True)
        await database["project_memberships"].create_index([("project_id", 1), ("email", 1)], unique=True)
        with ExitStack() as stack:
            for flag in ("customer_accounts", "account_subscriptions"):
                stack.enter_context(patch.object(settings.features, flag, True))
            for module in (auth_routes, account_routes, project_routes, subscription_routes, subscription_services, sync_usage, story_service, project_team_service, auth_dependency, project_authorization):
                stack.enter_context(patch.object(module, "db", database))
            app = FastAPI()
            for router in (auth_routes.router, account_routes.router, project_routes.router, project_team_routes.router): app.include_router(router)
            def session(): return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost")
            async with session() as owner, session() as member, session() as other:
                stage = "real_login_and_account_subscription"
                payload = {"name": "Synthetic", "email": emails[0], "password": "Synthetic-billing-fixture-only-724!"}
                assert (await owner.post('/auth/signup', json=payload)).status_code == 200
                assert (await owner.post('/auth/login', json={key: payload[key] for key in ("email", "password")})).status_code == 200
                account_id = (await owner.get('/account')).json()["account_id"]
                assert (await owner.patch('/account', json={"name": "Synthetic Billing Customer"})).status_code == 200
                response = await owner.post('/projects', json={"name": "Synthetic module", "created_by": emails[0]})
                assert response.status_code == 200
                project_id = response.json()["project_id"]
                assert (await owner.get('/account/subscription')).json()["subscription"]["usage"]["projects_used"] == 1
                results[stage] = True
                stage = "invitation_seats_and_shared_profile"
                response = await owner.post('/account/invitations', json={"email": emails[1]}); assert response.status_code == 201
                token = response.json()["token"]
                payload.update({"email": emails[1], "invitation_token": token})
                assert (await member.post('/auth/signup', json=payload)).status_code == 200
                assert (await owner.post(f'/projects/{project_id}/team', json={"email": emails[1], "role": "ADMIN"})).status_code == 200
                owner_sub = (await owner.get('/auth/me?refresh_usage=false')).json()["user"]["subscription"]
                member_sub = (await member.get('/auth/me?refresh_usage=false')).json()["user"]["subscription"]
                assert owner_sub == member_sub and owner_sub["usage"]["team_members_used"] == 1
                results[stage] = True
                stage = "central_assignment_permissions_and_cross_account_denial"
                assert (await member.post(f'/projects/{project_id}/team', json={"email": emails[0], "role": "ADMIN"})).status_code == 403
                payload.pop("invitation_token"); payload["email"] = emails[2]
                assert (await other.post('/auth/signup', json=payload)).status_code == 200
                assert (await other.get(f'/projects/{project_id}/team')).status_code == 404
                fixture_project = "FIX_" + uuid4().hex
                await database["projects"].insert_one({"project_id": fixture_project, "account_id": account_id, "name": "Assignment fixture", "created_by": emails[1], "agent_identities": {}, "created_at": "2026-11-12T00:00:00+00:00"})
                assert (await owner.get(f'/projects/{fixture_project}')).status_code == 404
                assert (await owner.post(f'/projects/{fixture_project}/team', json={"email": emails[0], "role": "ADMIN"})).status_code == 200
                assert (await owner.get(f'/projects/{fixture_project}')).status_code == 200
                results[stage] = True
                stage = "real_mongo_shared_ai_credit_contention_provider_double"
                await database["customer_accounts"].update_one({"_id": account_id}, {"$set": {"subscription.limits.ai_gen_limit": 1}})
                users = [await database["users"].find_one({"email": email}) for email in emails[:2]]
                for identity, project in zip(users, (fixture_project, project_id)):
                    user_id = str(identity["_id"])
                    redis_keys += [f"ai:rate:{project}:{user_id}:TEST_DESIGN", f"ai:concurrency:{project}:{user_id}:TEST_DESIGN"]
                service = AIUsageService(database=database, redis_backend=redis_client.redis_client, gateway=SyntheticGateway())
                outcomes = await asyncio.gather(*[service.execute(AIOperation.TEST_DESIGN, project, identity, LLMRequest(prompt="synthetic-only")) for identity, project in zip(users, (fixture_project, project_id))], return_exceptions=True)
                assert sum(isinstance(item, LLMResponse) for item in outcomes) == 1
                assert sum(isinstance(item, AIUsageError) for item in outcomes) == 1
                assert (await owner.get('/auth/me')).json()["user"]["subscription"]["usage"]["ai_gen_used"] == 1
                assert (await member.get('/auth/me')).json()["user"]["subscription"]["usage"]["ai_gen_used"] == 1
                results[stage] = True
                stage = "real_mongo_seat_contention_and_revoke"
                await database["customer_accounts"].update_one({"_id": account_id}, {"$set": {"subscription.limits.team_members_limit": 2}})
                outcomes = await asyncio.gather(*[owner.post('/account/invitations', json={"email": uuid4().hex + "@example.com"}) for _ in range(2)])
                assert sorted(item.status_code for item in outcomes) == [201, 403]
                invitation = next(item.json() for item in outcomes if item.status_code == 201)
                assert (await owner.delete('/account/invitations/' + invitation["invitation_id"])).status_code == 200
                assert (await owner.get('/account/subscription')).json()["subscription"]["usage"]["team_members_used"] == 1
                results[stage] = True
                stage = "real_billing_migration_fixture"
                identity = ObjectId(); legacy_id = "ACC_migration_fixture"
                source = {"_id": identity, "email": "billing-migration-fixture@example.com", "account_id": legacy_id, "subscription": deepcopy(owner_sub)}
                account = {"_id": legacy_id, "owner_user_id": str(identity), "status": "ACTIVE"}
                await database["users"].insert_one(source); await database["customer_accounts"].insert_one(account)
                source_snapshot = await database["users"].find_one({"_id": identity})
                plan = plan_subscriptions([account], [source], [], {}, [])
                assert not plan["errors"]
                await apply_subscriptions(database, plan, plan["plan_digest"], maintenance_confirmed=True)
                migrated = await database["customer_accounts"].find_one({"_id": legacy_id})
                assert migrated["billing_version"] == 1
                assert plan_subscriptions([migrated], [source], [], {}, [])["changes"] == []
                assert (await database["users"].find_one({"_id": identity}))["subscription"] == source_snapshot["subscription"]
                results[stage] = True
    except Exception as error:
        results["failure_stage"] = stage; results["failure_type"] = type(error).__name__
        if isinstance(error, AssertionError):
            import traceback
            results["assertion_line"] = traceback.extract_tb(error.__traceback__)[-1].lineno
    finally:
        try:
            for name in database.names:
                assert name.startswith(prefix)
                await asyncio.wait_for(db[name].drop(), 15)
            if redis_ready:
                for email in emails: await asyncio.to_thread(redis_client.delete_refresh_token, email)
                for key in redis_keys: await asyncio.to_thread(redis_client.redis_client.delete, key)
            cleanup = True
        except Exception: cleanup = False
        print(json.dumps({"real_development_services": results, "fixture_cleanup": cleanup, "external_provider_calls": 0}, indent=2))
    if "failure_type" in results or not cleanup: raise SystemExit(1)


if __name__ == "__main__": asyncio.run(main())
