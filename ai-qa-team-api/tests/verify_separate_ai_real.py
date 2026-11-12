"""Real development Mongo/Redis; synthetic provider, disposable namespace only."""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import json
from uuid import uuid4
from unittest.mock import patch
from bson import ObjectId
from verify_customer_accounts_real import FixtureDB
from app.config import settings
from app.db.connection import db
from app.models.subscription import Subscription
from app.services.ai_allowances import initialize_allowances
from app.services.ai_allowance_migration import plan_ai_allowances, apply_ai_allowances
from app.services.ai.ai_usage_service import AIUsageService
from app.services.ai.ai_usage_policy import AIOperation, AIUsageError
from app.services.ai.base_provider import LLMRequest, LLMResponse
from app.services.ai.llm_gateway import ResolvedLLMContext
from app.utils.redis_client import redis_client


class Gateway:
    def __init__(self, mode): self.mode = mode; self.calls = 0
    async def resolve(self, project, request): return ResolvedLLMContext(self.mode, "openai", "synthetic", None)
    async def generate_resolved(self, context, request): self.calls += 1; return LLMResponse("synthetic", "openai", "synthetic")


async def main():
    if settings.app_env.lower() not in {"development", "local", "test"}: raise SystemExit("Development services only.")
    prefix = "separate_ai_fixture_" + uuid4().hex + "_"; database = FixtureDB(prefix)
    results = {}; cleanup = False; stage = "readiness"; keys = []
    try:
        await asyncio.wait_for(db.command("ping"), 15); await asyncio.wait_for(asyncio.to_thread(redis_client.ping), 15)
        with ExitStack() as stack:
            for flag in ("customer_accounts", "account_subscriptions", "separate_ai_allowances"): stack.enter_context(patch.object(settings.features, flag, True))
            model = Subscription(); model.apply_plan_defaults()
            subscription = initialize_allowances(model.model_dump()); subscription["limits"].update({"managed_ai_credits_limit": 1, "byok_ai_requests_limit": 2})
            account_id = "ACC_" + uuid4().hex
            await database["customer_accounts"].insert_one({"_id": account_id, "status": "ACTIVE", "billing_version": 1, "subscription": subscription})
            users, projects = [], []
            for index in range(2):
                user = {"_id": ObjectId(), "email": uuid4().hex + "@example.com", "account_id": account_id, "account_role": "MEMBER", "account_state": "ACTIVE"}
                project = prefix + str(index)
                await database["users"].insert_one(user)
                await database["projects"].insert_one({"project_id": project, "account_id": account_id, "created_by": user["email"]})
                users.append(user); projects.append(project)
                keys += [f"ai:rate:{project}:{user['_id']}:TEST_DESIGN", f"ai:concurrency:{project}:{user['_id']}:TEST_DESIGN"]
            stage = "real_mongo_shared_managed_contention"
            gateway = Gateway("MANAGED"); service = AIUsageService(database=database, redis_backend=redis_client, gateway=gateway)
            outcomes = await asyncio.gather(*[service.execute(AIOperation.TEST_DESIGN, project, user, LLMRequest(prompt="synthetic")) for project,user in zip(projects,users)], return_exceptions=True)
            assert sum(isinstance(item, LLMResponse) for item in outcomes) == 1 and gateway.calls == 1
            assert sum(isinstance(item, AIUsageError) for item in outcomes) == 1
            results[stage] = True
            stage = "independent_byok_pool_no_mode_reset"
            gateway = Gateway("BYOK"); service = AIUsageService(database=database, redis_backend=redis_client, gateway=gateway)
            for _ in range(2): await service.execute(AIOperation.TEST_DESIGN, projects[1], users[1], LLMRequest(prompt="synthetic"))
            try: await service.execute(AIOperation.TEST_DESIGN, projects[1], users[1], LLMRequest(prompt="synthetic"))
            except AIUsageError: pass
            else: raise AssertionError()
            account = await database["customer_accounts"].find_one({"_id": account_id})
            assert account["subscription"]["usage"]["managed_ai_credits_used"] == 1
            assert account["subscription"]["usage"]["byok_ai_requests_used"] == 2 and gateway.calls == 2
            results[stage] = True
            stage = "real_split_migration_repeatable"
            legacy = deepcopy(subscription); legacy.pop("ai_allowance_version"); legacy["usage"]["ai_gen_used"] = 3
            legacy_id = "ACC_" + uuid4().hex
            await database["customer_accounts"].insert_one({"_id": legacy_id, "status": "ACTIVE", "billing_version": 1, "subscription": legacy})
            before = await database["customer_accounts"].find_one({"_id": legacy_id})
            plan = plan_ai_allowances([before], [], [])
            assert not plan["errors"]
            await apply_ai_allowances(database, plan, plan["plan_digest"], maintenance_confirmed=True)
            after = await database["customer_accounts"].find_one({"_id": legacy_id})
            assert after["subscription"]["usage"]["managed_ai_credits_used"] == 3 and after["subscription"]["usage"]["byok_ai_requests_used"] == 3
            assert plan_ai_allowances([after], [], [])["changes"] == []
            results[stage] = True
    except Exception as error:
        results["failure_stage"] = stage; results["failure_type"] = type(error).__name__
    finally:
        try:
            for name in database.names:
                assert name.startswith(prefix); await asyncio.wait_for(db[name].drop(), 15)
            for key in keys: await asyncio.to_thread(redis_client.delete, key)
            cleanup = True
        except Exception: cleanup = False
        print(json.dumps({"real_development_services": results, "fixture_cleanup": cleanup, "external_provider_calls": 0}, indent=2))
    if not cleanup or "failure_type" in results: raise SystemExit(1)


if __name__ == "__main__": asyncio.run(main())
