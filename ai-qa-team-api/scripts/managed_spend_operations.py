"""Development-only private spend cutover/reconciliation; dry run by default."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.connection import db
from app.services.ai.managed_spend import ManagedSpend
from app.services.ai.spend_cutover import plan_cutover, apply_cutover
from app.services.resource_quota import fingerprint


async def main():
    if settings.app_env.lower() not in {"development", "local", "test"}:
        raise SystemExit("Only explicitly configured development services are supported.")
    parser = argparse.ArgumentParser()
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--opening-balances", type=Path)
    operation.add_argument("--usage-id")
    parser.add_argument("--provider-proof", type=Path, help="Private JSON: reference, input_tokens, output_tokens, response_model")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-digest")
    parser.add_argument("--maintenance-confirmed", action="store_true")
    args = parser.parse_args()
    if args.opening_balances:
        plan = await plan_cutover(db, json.loads(args.opening_balances.read_text(encoding="utf-8")))
        if args.apply:
            await apply_cutover(db, plan, args.expected_digest, maintenance_confirmed=args.maintenance_confirmed)
        print(json.dumps({"already_initialized": plan.get("already_initialized", False), "plan_digest": plan["plan_digest"], "budget_count": len(plan["changes"])}))
        return
    if not args.usage_id or not args.provider_proof:
        raise SystemExit("Choose a reviewed cutover or one exact reservation and provider proof.")
    record = await db["ai_spend_reservations"].find_one({"_id": args.usage_id})
    proof = json.loads(args.provider_proof.read_text(encoding="utf-8"))
    if not record or record["state"] not in ("RESERVED", "SUBMITTED", "CALLING", "UNKNOWN") or not proof.get("reference"):
        raise SystemExit("An unresolved reservation and explicit provider evidence are required.")
    plan_digest = fingerprint([record, proof])
    if args.apply:
        if not args.maintenance_confirmed or plan_digest != args.expected_digest:
            raise SystemExit("Matching reviewed proof and stopped writers are required.")
        await ManagedSpend(db).settle(record, input_tokens=proof.get("input_tokens"), output_tokens=proof.get("output_tokens"),
            response_model=proof.get("response_model"), proof={"reference": proof["reference"], "record_digest": fingerprint(record)})
    print(json.dumps({"usage_id": args.usage_id, "plan_digest": plan_digest, "applied": args.apply}))


if __name__ == "__main__": asyncio.run(main())
