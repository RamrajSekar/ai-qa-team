"""Default dry-run. Explicit mapping; no production or automatic startup migration."""
import argparse
import asyncio
import json
from pathlib import Path

from app.db.connection import db
from app.services.account_migration import plan_accounts, apply_accounts


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-digest")
    parser.add_argument("--maintenance-confirmed", action="store_true")
    args = parser.parse_args()
    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    users = await db["users"].find({}, {"email": 1, "account_id": 1, "account_role": 1, "account_state": 1}).to_list(None)
    projects = await db["projects"].find({}, {"project_id": 1, "created_by": 1, "legacy_created_by": 1, "account_id": 1}).to_list(None)
    memberships = await db["project_memberships"].find({}, {"membership_id": 1, "project_id": 1, "email": 1, "status": 1, "legacy_status": 1, "account_id": 1}).to_list(None)
    accounts = await db["customer_accounts"].find({}, {"owner_user_id": 1, "status": 1}).to_list(None)
    plan = plan_accounts(users, projects, memberships, mapping, accounts)
    if args.apply:
        await apply_accounts(db, plan, args.expected_digest, maintenance_confirmed=args.maintenance_confirmed)
    # Never print user documents, email addresses, subscriptions or secrets.
    print(json.dumps({"applied": args.apply, "plan_digest": plan["plan_digest"], "account_count": len(plan["accounts"]),
                      "account_ids": [account["_id"] for account in plan["accounts"]],
                      "change_count": len(plan["changes"]), "errors": plan["errors"]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
