"""Development-only, default dry-run; changes one Free allowance field only."""
import argparse
import asyncio
import json
from app.config import settings
from app.db.connection import db
from app.services.free_member_allowance import plan_free_allowance, apply_free_allowance


async def main():
    if settings.app_env.lower() not in {"development", "local", "test"}:
        raise SystemExit("Development services only.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    accounts = await db["customer_accounts"].find({"billing_version": 1, "subscription.plan": "free"}, {"billing_version": 1, "subscription.plan": 1, "subscription.limits.team_members_limit": 1}).to_list(None)
    plan = plan_free_allowance(accounts)
    if args.apply: await apply_free_allowance(db, plan, args.expected_digest)
    print(json.dumps({"applied": args.apply, **plan}, indent=2))


if __name__ == "__main__": asyncio.run(main())
