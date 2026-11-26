"""Reviewed opening spend balances. Never initializes at startup or on a request."""
from datetime import datetime, timezone
from app.config import settings
from app.services.resource_quota import ResourceQuota, fingerprint


async def plan_cutover(database, opening):
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    if (opening.get("period") != period or opening.get("currency") != "USD" or not opening.get("provider_report_reference")
            or not isinstance(opening.get("accounts"), dict) or "platform_spent_micro_usd" not in opening
            or not settings.managed_spend.cutover_id):
        raise ValueError("Reviewed current-period USD opening balances and a report reference are required.")
    values = [opening["platform_spent_micro_usd"], *opening["accounts"].values()]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        raise ValueError("Opening spend must use nonnegative integer micro-USD.")
    if opening["platform_spent_micro_usd"] < sum(opening["accounts"].values()):
        raise ValueError("Platform opening spend cannot be below account opening spend.")
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Unknown historical attribution is included conservatively, never treated as free spend.
    owners = await database["ai_usage_records"].distinct("billing_owner", {"ai_mode": {"$ne": "BYOK"}, "$or": [
        {"billing_period_start": {"$gte": period + "-01"}}, {"started_at": {"$gte": start}}]})
    if any(owner not in opening["accounts"] for owner in owners):
        raise ValueError("Every historical Managed billing owner requires an opening balance.")
    if await database["ai_usage_records"].count_documents({"status": "STARTED"}):
        raise ValueError("Reconcile active/uncertain AI work before cutover.")
    before = await database["ai_spend_control"].find_one({"_id": "managed"})
    if before and before.get("initialized"):
        if before.get("cutover_id") != settings.managed_spend.cutover_id:
            raise ValueError("Existing spend policy cannot be replaced by an initialization.")
        return {"already_initialized": True, "changes": [], "plan_digest": fingerprint(before)}
    rows = [{"_id": fingerprint(["account", owner, period]), "spent_micro_usd": amount,
        "reserved_micro_usd": 0, "period": period} for owner, amount in sorted(opening["accounts"].items())]
    rows.append({"_id": fingerprint(["platform", period]), "spent_micro_usd": opening["platform_spent_micro_usd"], "reserved_micro_usd": 0, "period": period})
    prior = await database["ai_spend_budgets"].find({"period": period}).to_list(None)
    if any(row.get("spent_micro_usd", 0) or row.get("reserved_micro_usd", 0) for row in prior):
        raise ValueError("Existing spend cannot be reset by initialization.")
    plan = {"cutover_id": settings.managed_spend.cutover_id, "opening": opening, "changes": rows, "before": before, "budget_before": prior}
    return {**plan, "plan_digest": fingerprint(plan)}


async def apply_cutover(database, plan, expected_digest, *, maintenance_confirmed=False):
    if (not maintenance_confirmed or plan.get("already_initialized") or expected_digest != plan.get("plan_digest")
            or fingerprint({key: value for key, value in plan.items() if key != "plan_digest"}) != expected_digest):
        raise ValueError("Matching reviewed cutover and stopped writers are required.")
    async def work(session):
        if await database["ai_spend_control"].find_one({"_id": "managed"}, session=session) != plan["before"]:
            raise ValueError("Spend policy changed; review a new plan.")
        current = await database["ai_spend_budgets"].find({"period": plan["opening"]["period"]}, session=session).to_list(None)
        if fingerprint(sorted(current, key=lambda row: row["_id"])) != fingerprint(sorted(plan["budget_before"], key=lambda row: row["_id"])):
            raise ValueError("Spend balances changed; review a new plan.")
        if await database["ai_usage_records"].count_documents({"status": "STARTED"}, session=session):
            raise ValueError("Active AI work blocks cutover.")
        for row in plan["changes"]:
            await database["ai_spend_budgets"].replace_one({"_id": row["_id"]}, row, upsert=True, session=session)
        await database["ai_spend_control"].replace_one({"_id": "managed"}, {"_id": "managed", "initialized": True,
            "halted": False, "cutover_id": plan["cutover_id"], "plan_digest": expected_digest}, upsert=True, session=session)
        await database["ai_spend_cutover_receipts"].insert_one({"_id": expected_digest, "opening": plan["opening"],
            "at": datetime.now(timezone.utc)}, session=session)
    await ResourceQuota(database).transaction(work)
