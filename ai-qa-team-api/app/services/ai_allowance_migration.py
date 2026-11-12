"""Explicit split of historical shared usage; unknown attribution consumes both pools."""
from datetime import datetime, timezone
from copy import deepcopy
from app.services.ai_allowances import configured_limits
from app.services.approved_visual_run import digest


def period_key(value):
    if not value: return None
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def plan_ai_allowances(accounts, projects, records, *, now=None):
    now = now or datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()
    end = datetime(now.year + (now.month == 12), 1 if now.month == 12 else now.month + 1, 1, tzinfo=timezone.utc).isoformat()
    changes, errors = [], []
    for account in accounts:
        before = deepcopy(account.get("subscription", {}))
        if before.get("ai_allowance_version") == 1: continue
        identity = account["_id"]
        if account.get("billing_version") != 1:
            errors.append("Account billing migration required: " + identity); continue
        project_ids = {item["project_id"] for item in projects if item.get("account_id") == identity}
        related = [item for item in records if item.get("account_id") == identity or (not item.get("account_id") and (item.get("billing_owner") == identity or item.get("project_id") in project_ids))]
        if any(item.get("status") == "STARTED" for item in related):
            errors.append("Reconcile active/unfinished AI reservations: " + identity); continue
        try:
            limits = configured_limits(before["plan"])
            current = [item for item in related if period_key(item.get("billing_period_start")) == start]
            historic = before.get("usage", {}).get("ai_gen_used", 0) if period_key(before.get("ai_usage_period_start")) in (None, start) else 0
            if not isinstance(historic, int) or historic < 0: raise ValueError()
            managed = byok = known = observed_unknown = 0
            for item in current:
                units = item.get("credits_consumed", 0)
                if not isinstance(units, int) or units < 0: raise ValueError()
                if item.get("ai_mode") == "MANAGED": managed += units; known += units
                elif item.get("ai_mode") == "BYOK": byok += int(units > 0); known += units
                else: observed_unknown += units
            unknown = max(historic - known, observed_unknown, 0)
        except (ValueError, KeyError, TypeError):
            errors.append("Review invalid legacy AI period/usage: " + identity); continue
        after = deepcopy(before)
        after.setdefault("usage", {}).update({"managed_ai_credits_used": managed + unknown, "byok_ai_requests_used": byok + unknown,
            "ai_gen_used": max(historic, known + observed_unknown)})
        after.setdefault("limits", {}).update(limits)
        after.update({"ai_allowance_version": 1, "ai_usage_period_start": start, "ai_usage_period_end": end,
            "ai_allowance_migration": {"unknown_units": unknown, "method": "CONSERVATIVE_BOTH", "legacy_aggregate": historic}})
        changes.append({"account_id": identity, "before": before, "after": after})
    plan = {"changes": changes, "errors": sorted(set(errors)), "source_digest": digest({"projects": projects, "records": records})}
    return {**plan, "plan_digest": digest(plan)}


async def apply_ai_allowances(database, plan, expected_digest, *, maintenance_confirmed=False):
    if plan["errors"] or expected_digest != plan["plan_digest"] or not maintenance_confirmed:
        raise ValueError("A matching conflict-free AI plan and stopped writers are required.")
    for item in plan["changes"]:
        result = await database["customer_accounts"].update_one({"_id": item["account_id"], "billing_version": 1, "status": "ACTIVE", "subscription": item["before"]},
            {"$set": {"subscription": item["after"]}})
        if result.matched_count != 1: raise ValueError("AI usage changed. Stop and generate a new dry run.")
