"""Read-only by default. Existing-data apply requires explicit reviewed maintenance."""
import argparse
import asyncio
import json
from pathlib import Path
from app.db.connection import db
from app.config import settings
from app.services.account_subscription_migration import plan_subscriptions, apply_subscriptions


async def main():
    if settings.app_env.lower() not in {"development", "local", "test"}:
        raise SystemExit("This migration helper supports explicitly configured development services only.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", help="Optional private subscription_sources account-ID to user-ID mapping")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-digest")
    parser.add_argument("--maintenance-confirmed", action="store_true")
    args = parser.parse_args()
    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8")) if args.mapping else {}
    accounts = await db["customer_accounts"].find({"status": "ACTIVE"}).to_list(None)
    users = await db["users"].find({}, {"email": 1, "account_id": 1, "subscription": 1}).to_list(None)
    projects = await db["projects"].find({}, {"project_id": 1, "account_id": 1}).to_list(None)
    invitations = await db["account_invitations"].find({}, {"account_id": 1, "status": 1}).to_list(None)
    counts = {}
    for account in accounts:
        project_ids = [project["project_id"] for project in projects if project.get("account_id") == account["_id"]]
        values = {"projects_used": len(project_ids)}
        query = {"project_id": {"$in": project_ids}}
        if await db["ai_usage_records"].count_documents({**query, "status": "STARTED"}):
            raise SystemExit("Active or unresolved AI reservations found; reconcile before billing migration.")
        for collection in ("stories", "scenarios", "testcases", "executions"):
            values[collection + "_used"] = await db[collection].count_documents(query)
        for level in ("basic", "medium", "advanced"):
            values["testcases_" + level + "_used"] = await db["testcases"].count_documents({**query, "$or": [{"level": level}, {"complexity": level}]})
        counts[account["_id"]] = values
    plan = plan_subscriptions(accounts, users, projects, counts, invitations, mapping)
    if args.apply:
        await apply_subscriptions(db, plan, args.expected_digest, maintenance_confirmed=args.maintenance_confirmed)
    print(json.dumps({"applied": args.apply, "plan_digest": plan["plan_digest"], "account_count": len(plan["changes"]),
        "errors": plan["errors"], "accounts": [{"account_id": change["account_id"], "plan": change["subscription"]["plan"], "usage": change["subscription"]["usage"]} for change in plan["changes"]]}, indent=2))


if __name__ == "__main__": asyncio.run(main())
