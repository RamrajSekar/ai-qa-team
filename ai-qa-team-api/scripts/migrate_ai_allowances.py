"""Development-only, read-only unless explicitly applying a reviewed plan."""
import argparse
import asyncio
import json
from app.config import settings
from app.db.connection import db
from app.services.ai_allowance_migration import plan_ai_allowances, apply_ai_allowances


async def main():
    if settings.app_env.lower() not in {"development", "local", "test"}: raise SystemExit("Development services only.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true"); parser.add_argument("--expected-digest"); parser.add_argument("--maintenance-confirmed", action="store_true")
    args = parser.parse_args()
    accounts = await db["customer_accounts"].find({"status": "ACTIVE"}, {"subscription": 1, "billing_version": 1}).to_list(None)
    projects = await db["projects"].find({}, {"project_id": 1, "account_id": 1}).to_list(None)
    records = await db["ai_usage_records"].find({}, {"account_id": 1, "project_id": 1, "billing_owner": 1, "ai_mode": 1, "status": 1, "credits_consumed": 1, "billing_period_start": 1}).to_list(None)
    plan = plan_ai_allowances(accounts, projects, records)
    if args.apply: await apply_ai_allowances(db, plan, args.expected_digest, maintenance_confirmed=args.maintenance_confirmed)
    print(json.dumps({"applied": args.apply, "plan_digest": plan["plan_digest"], "errors": plan["errors"], "accounts": [{"account_id": item["account_id"],
        "managed_used": item["after"]["usage"]["managed_ai_credits_used"], "byok_used": item["after"]["usage"]["byok_ai_requests_used"],
        "managed_limit": item["after"]["limits"]["managed_ai_credits_limit"], "byok_limit": item["after"]["limits"]["byok_ai_requests_limit"],
        "unattributed_legacy_units": item["after"]["ai_allowance_migration"]["unknown_units"]} for item in plan["changes"]]}, indent=2))


if __name__ == "__main__": asyncio.run(main())
