"""Development-only, explicit selection, dry-run by default. No production cutover."""
import argparse
import asyncio
import json
from pathlib import Path

from app.config import settings
from app.db.connection import db
from app.services.account_entitlements import plan_entitlements, apply_entitlements, inventory_counts


async def main():
    if settings.app_env.lower() not in {"development", "local", "test"}:
        raise SystemExit("Only explicitly configured development services are supported.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", required=True, help="Private JSON: account ID to free/team/business")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-digest")
    parser.add_argument("--maintenance-confirmed", action="store_true")
    args = parser.parse_args()
    selections = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    if not isinstance(selections, dict) or not selections:
        raise SystemExit("Supply explicit account selections.")
    accounts = await db["customer_accounts"].find({"_id": {"$in": list(selections)}}).to_list(None)
    inventory = {account["_id"]: await inventory_counts(db, account) for account in accounts}
    plan = plan_entitlements(accounts, selections, inventory)
    for identity in selections:
        if await db["ai_usage_records"].count_documents({"account_id": identity, "status": "STARTED"}):
            raise SystemExit("Reconcile active/uncertain AI work before reviewing policy adoption.")
    if args.apply:
        await apply_entitlements(db, plan, args.expected_digest, maintenance_confirmed=args.maintenance_confirmed)
    print(json.dumps({"applied": args.apply, "plan_digest": plan["plan_digest"], "errors": plan["errors"],
        "accounts": [{"account_id": change["account_id"], "from": change["before"]["subscription"]["plan"],
            "to": change["after"]["plan"], "limits": change["after"]["limits"],
            "over_capacity": change["over_capacity"]} for change in plan["changes"]]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
