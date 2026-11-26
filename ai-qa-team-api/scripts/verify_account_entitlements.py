"""Opt-in loopback-only policy/concurrency qualification; never application data."""
import argparse
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(MONGO_URI="mongodb://127.0.0.1:27129", MONGO_DB="qa_pricing_fixture_only",
    REDIS_HOST="127.0.0.1", REDIS_PORT="6399", REDIS_USERNAME="", REDIS_PASSWORD="",
    JWT_SECRET_KEY="local-pricing-fixture-only", SESSION_SECRET_KEY="local-pricing-fixture-only")
from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings, FeatureFlags
from app.models.subscription import Subscription
from app.services.account_entitlements import plan_entitlements, apply_entitlements
from app.services.account_billing import change_seats
from app.services.resource_quota import ResourceQuota


async def verify(db):
    checks = []

    async def fixture():
        identity = "ACC_" + uuid4().hex
        user = {"_id": ObjectId(), "email": uuid4().hex + "@example.com", "account_id": identity,
            "account_state": "ACTIVE", "account_role": "OWNER"}
        model = Subscription(); model.apply_plan_defaults()
        sub = model.model_dump()
        sub.update(ai_allowance_version=1, ai_usage_period_start="2026-11-01T00:00:00+00:00",
            ai_usage_period_end="2026-12-01T00:00:00+00:00")
        sub["usage"].update(managed_ai_credits_used=7, byok_ai_requests_used=3, ai_gen_used=10)
        row = {"_id": identity, "owner_user_id": str(user["_id"]), "status": "ACTIVE", "billing_version": 1, "subscription": sub}
        await db["customer_accounts"].insert_one(row)
        user["subscription"] = deepcopy(sub)
        await db["users"].insert_one(user)
        return await db["users"].find_one({"_id": user["_id"]}), await db["customer_accounts"].find_one({"_id": identity})

    async def adopt(row, target="team"):
        plan = plan_entitlements([row], {row["_id"]: target})
        assert not plan["errors"], plan["errors"]
        await apply_entitlements(db, plan, plan["plan_digest"], maintenance_confirmed=True)
        return plan

    async def expect_error(work, code=None):
        try: await work
        except (ValueError, HTTPException) as error:
            if code: assert isinstance(error, HTTPException) and error.status_code == code
            return
        raise AssertionError("Expected rejection")

    async def run(name, work):
        await work(); checks.append({"name": name, "passed": True})

    async def migration():
        user, row = await fixture(); _, foreign = await fixture()
        plan = await adopt(row)
        after = await db["customer_accounts"].find_one({"_id": row["_id"]})
        assert after["subscription"]["usage"] == row["subscription"]["usage"]
        assert after["subscription"]["ai_usage_period_start"] == row["subscription"]["ai_usage_period_start"]
        assert (await db["users"].find_one({"_id": user["_id"]}))["subscription"] == user["subscription"]
        assert await db["customer_accounts"].find_one({"_id": foreign["_id"]}) == foreign
        assert plan_entitlements([after], {row["_id"]: "team"})["changes"] == []
        await apply_entitlements(db, plan, plan["plan_digest"], maintenance_confirmed=True)
        assert await db["account_entitlement_receipts"].count_documents({"account_id": row["_id"]}) == 1
    await run("migration_preserves_usage_period_legacy_and_other_account_and_receipt_is_idempotent", migration)

    async def stale():
        _, row = await fixture(); plan = plan_entitlements([row], {row["_id"]: "business"})
        await db["customer_accounts"].update_one({"_id": row["_id"]}, {"$inc": {"subscription.usage.stories_used": 1}})
        await expect_error(apply_entitlements(db, plan, plan["plan_digest"], maintenance_confirmed=True))
        assert await db["account_entitlement_receipts"].count_documents({"account_id": row["_id"]}) == 0
    await run("stale_usage_invalidates_review_without_partial_receipt", stale)

    async def stale_inventory():
        _, row = await fixture(); plan = plan_entitlements([row], {row["_id"]: "team"})
        await db["projects"].insert_one({"project_id": uuid4().hex, "account_id": row["_id"]})
        await expect_error(apply_entitlements(db, plan, plan["plan_digest"], maintenance_confirmed=True))
        assert (await db["customer_accounts"].find_one({"_id": row["_id"]}))["subscription"]["plan"] == "free"
    await run("unaccounted_inventory_blocks_adoption_without_resetting_counters", stale_inventory)

    async def in_flight():
        for collection, record in (("ai_usage_records", {"status": "STARTED"}),
                ("resource_quota_reservations", {"state": "RESERVED", "owner_collection": "customer_accounts"})):
            _, row = await fixture(); plan = plan_entitlements([row], {row["_id"]: "team"})
            record = {**record, "account_id": row["_id"], "owner_id": row["_id"]}
            await db[collection].insert_one(record)
            await expect_error(apply_entitlements(db, plan, plan["plan_digest"], maintenance_confirmed=True))
            assert (await db["customer_accounts"].find_one({"_id": row["_id"]}))["subscription"]["plan"] == "free"
    await run("active_ai_and_unsettled_resources_block_policy_change", in_flight)

    async def resource_race(kind):
        user, row = await fixture(); await adopt(row)
        await db["customer_accounts"].update_one({"_id": row["_id"]}, {"$set": {f"subscription.limits.{kind}_limit": 1}})
        if kind == "stories": await db["projects"].insert_one({"project_id": row["_id"], "account_id": row["_id"]})
        async def create():
            project = uuid4().hex if kind == "projects" else row["_id"]
            doc = {"project_id": project, "account_id": row["_id"], "created_by": user["email"], "title": "Fixture"}
            member = {"project_id": project, "account_id": row["_id"], "email": user["email"], "role": "ADMIN"} if kind == "projects" else None
            return await ResourceQuota(db).create_account_resource(user, kind, doc, creator_membership=member)
        results = await asyncio.gather(*(create() for _ in range(5)), return_exceptions=True)
        assert sum(isinstance(result, dict) for result in results) == 1, results
        assert all(isinstance(result, dict) or isinstance(result, HTTPException) and result.status_code == 403 for result in results)
        after = await db["customer_accounts"].find_one({"_id": row["_id"]})
        assert after["subscription"]["usage"][kind + "_used"] == 1
        assert await db[kind].count_documents({"created_by": user["email"]}) == 1
        if kind == "projects": assert await db["project_memberships"].count_documents({"email": user["email"]}) == 1
        assert after["subscription"]["usage"]["managed_ai_credits_used"] == 7
    await run("five_project_writers_share_one_last_slot_and_atomic_creator_membership", lambda: resource_race("projects"))
    await run("five_story_writers_share_one_last_slot", lambda: resource_race("stories"))

    async def rollback():
        user, row = await fixture(); await adopt(row)
        project = uuid4().hex; member = {"_id": "duplicate-fixture", "project_id": project, "email": user["email"]}
        await db["project_memberships"].insert_one(deepcopy(member))
        await expect_error(ResourceQuota(db).create_account_resource(user, "projects",
            {"project_id": project, "account_id": row["_id"], "created_by": user["email"]}, creator_membership=member), 409)
        assert await db["projects"].count_documents({"project_id": project}) == 0
        assert (await db["customer_accounts"].find_one({"_id": row["_id"]}))["subscription"]["usage"]["projects_used"] == 0
    await run("membership_insert_failure_rolls_back_project_and_capacity", rollback)

    async def foreign_project():
        user, row = await fixture(); await adopt(row)
        await db["projects"].insert_one({"project_id": uuid4().hex, "account_id": "ACC_foreign"})
        await expect_error(ResourceQuota(db).create_account_resource(user, "stories",
            {"project_id": "missing-or-foreign", "created_by": user["email"]}), 403)
    await run("foreign_or_missing_story_project_cannot_consume_or_create", foreign_project)

    async def shared_cases():
        user, row = await fixture(); await adopt(row, "business")
        await db["customer_accounts"].update_one({"_id": row["_id"]}, {"$set": {"subscription.limits.testcases_limit": 1}})
        quota = ResourceQuota(db)
        results = await asyncio.gather(quota.reserve(user, "P1", "testcases", 1, "medium"),
            quota.reserve(user, "P1", "testcases", 1, "advanced"), return_exceptions=True)
        admitted = [value for value in results if isinstance(value, dict)]
        assert len(admitted) == 1
        assert any(isinstance(value, HTTPException) and value.status_code == 403 for value in results)
        reservation = admitted[0]
        await quota.persist(reservation, {"project_id": "P1", "created_by": user["email"], "complexity": reservation["tier"]}, 0)
        await quota.settle(reservation)
        after = await db["customer_accounts"].find_one({"_id": row["_id"]})
        assert after["subscription"]["usage"]["testcases_used"] == 1
    await run("business_medium_and_advanced_share_one_total_last_slot", shared_cases)

    async def seats():
        _, row = await fixture(); await adopt(row)
        await db["customer_accounts"].update_one({"_id": row["_id"]}, {"$set": {"subscription.limits.team_members_limit": 1}})
        snapshot = await db["customer_accounts"].find_one({"_id": row["_id"]})
        results = await asyncio.gather(*(change_seats(db, snapshot, 1) for _ in range(5)), return_exceptions=True)
        assert sum(value is None for value in results) == 1
        await db["customer_accounts"].update_one({"_id": row["_id"]}, {"$set": {"subscription.limits.team_members_limit": 0}})
        await expect_error(change_seats(db, snapshot, 1), 403)
    await run("seat_reservations_contend_and_reject_stale_pre_downgrade_limit", seats)

    async def stale_ai():
        from app.services.ai.ai_usage_service import AIUsageService
        from app.services.ai.ai_usage_policy import get_ai_usage_policy, AIOperation, AIUsageError
        _, row = await fixture(); await adopt(row)
        original = db["customer_accounts"]
        class Collection:
            def __getattr__(self, name): return getattr(original, name)
            async def find_one_and_update(self, query, update, **kwargs):
                await original.update_one({"_id": row["_id"]}, {"$set": {"subscription.limits.managed_ai_credits_limit": 0}})
                return await original.find_one_and_update(query, update, **kwargs)
        class Database:
            def __getitem__(self, name): return Collection() if name == "customer_accounts" else db[name]
        service = AIUsageService(database=Database(), gateway=object(), redis_backend=object())
        try:
            await service._reserve(row["_id"], get_ai_usage_policy(AIOperation.TEST_DESIGN), datetime(2026, 11, 26, tzinfo=timezone.utc))
        except AIUsageError as error: assert error.status_code == 403
        else: raise AssertionError("Stale AI allowance was spent")
        assert (await original.find_one({"_id": row["_id"]}))["subscription"]["usage"]["managed_ai_credits_used"] == 7
    await run("ai_reservation_cannot_spend_stale_pre_downgrade_allowance", stale_ai)

    async def downgrade():
        user, row = await fixture(); await adopt(row, "business")
        await db["customer_accounts"].update_one({"_id": row["_id"]}, {"$set": {"subscription.usage.projects_used": 2}})
        before = await db["customer_accounts"].find_one({"_id": row["_id"]})
        plan = await adopt(before, "free")
        assert plan["changes"][0]["over_capacity"]["projects_limit"] == 2
        project = {"project_id": uuid4().hex, "account_id": row["_id"], "created_by": user["email"]}
        member = {"project_id": project["project_id"], "email": user["email"]}
        await expect_error(ResourceQuota(db).create_account_resource(user, "projects", project, creator_membership=member), 403)
        assert (await db["customer_accounts"].find_one({"_id": row["_id"]}))["subscription"]["usage"] == before["subscription"]["usage"]
    await run("over_capacity_downgrade_preserves_usage_and_blocks_new_creation", downgrade)

    async def cli():
        from scripts import migrate_account_entitlements as migration_cli
        _, row = await fixture()
        with tempfile.TemporaryDirectory(prefix="qa_entitlement_cli_") as directory:
            mapping = Path(directory) / "mapping.json"
            mapping.write_text(json.dumps({row["_id"]: "team"}), encoding="utf-8")
            async def invoke(*extra):
                output = io.StringIO()
                with patch.object(migration_cli, "db", db), patch.object(settings, "app_env", "test"), \
                        patch.object(sys, "argv", ["migration", "--mapping", str(mapping), *extra]), redirect_stdout(output):
                    await migration_cli.main()
                return json.loads(output.getvalue())
            dry = await invoke()
            assert not dry["applied"] and len(dry["accounts"]) == 1
            assert (await db["customer_accounts"].find_one({"_id": row["_id"]}))["subscription"]["plan"] == "free"
            with patch.object(migration_cli, "db", db):
                try: await invoke("--apply", "--expected-digest", "stale", "--maintenance-confirmed")
                except ValueError: pass
                else: raise AssertionError("Unreviewed CLI apply succeeded")
            applied = await invoke("--apply", "--expected-digest", dry["plan_digest"], "--maintenance-confirmed")
            assert applied["applied"]
            assert (await invoke())["accounts"] == []
    await run("development_cli_dry_run_reviewed_apply_and_repeat_are_safe", cli)
    return checks


async def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--confirm-isolated-local", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27129/?replicaSet=qaTestDesign", serverSelectionTimeoutMS=5000, socketTimeoutMS=10000)
    name = "qa_entitlements_" + uuid4().hex
    try:
        assert (await client.admin.command("hello")).get("setName") == "qaTestDesign"
        with patch.object(settings, "features", FeatureFlags(customer_accounts=True, account_subscriptions=True)):
            checks = await verify(client[name])
    finally:
        await client.drop_database(name); client.close()
    report = {"checks": checks, "database": "ephemeral-loopback-only", "cleanup": "generated database dropped", "providers": "none"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": asyncio.run(main())
