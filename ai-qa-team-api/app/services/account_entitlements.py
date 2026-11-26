"""Explicit reviewed account policy adoption. No startup, login or purchase caller."""
from copy import deepcopy
from datetime import datetime, timezone

from app.app_config.plan_limits import plan_limits
from app.services.ai_allowances import configured_limits
from app.services.resource_quota import ResourceQuota, fingerprint


def entitlement_limits(subscription, target):
    if target not in ("free", "team", "business"):
        raise ValueError("Select Free, Team or Business explicitly; legacy plans are never relabelled.")
    limits = {key: value for key, value in plan_limits(target).items() if key.endswith("_limit")}
    limits.update(configured_limits(target))
    # Test Design adoption neither sells nor revokes historical execution capacity.
    limits["executions_limit"] = subscription.get("limits", {}).get("executions_limit", 0)
    return limits


async def inventory_counts(database, account, *, session=None):
    options = {"session": session} if session is not None else {}
    identity = account["_id"]
    projects = await database["projects"].find({"account_id": identity}, {"project_id": 1}, **options).to_list(None)
    query = {"project_id": {"$in": [project["project_id"] for project in projects]}}
    counts = {"projects_used": len(projects)}
    for kind in ("stories", "scenarios", "testcases"):
        counts[kind + "_used"] = await database[kind].count_documents(query, **options)
    for tier in ("basic", "medium", "advanced"):
        counts[f"testcases_{tier}_used"] = await database["testcases"].count_documents({**query, "$or": [
            {"complexity": tier}, {"complexity": None, "level": {"$in": [tier, None] if tier == "basic" else [tier]}}]}, **options)
    members = await database["users"].find({"account_id": identity, "account_state": "ACTIVE"},
        {"email": 1}, **options).to_list(None)
    emails = {user["email"].strip().lower() for user in members}
    pending = await database["account_invitations"].find({"account_id": identity, "status": {"$in": ["PENDING", "CLAIMED"]}},
        {"email": 1}, **options).to_list(None)
    counts["team_members_used"] = len({str(user["_id"]) for user in members if str(user["_id"]) != account.get("owner_user_id")})
    counts["team_members_used"] += len({invite["email"].strip().lower() for invite in pending} - emails)
    return counts


def plan_entitlements(accounts, selections, inventory=None):
    """Snapshots/digest are private review material, not a public update payload."""
    changes, errors = [], []
    indexed = {account["_id"]: account for account in accounts}
    for identity, target in sorted(selections.items()):
        account = indexed.get(identity)
        if not account or account.get("status") != "ACTIVE" or account.get("billing_version") != 1:
            errors.append(f"Active migrated account required: {identity}"); continue
        before = deepcopy(account.get("subscription", {}))
        if (not isinstance(before, dict) or before.get("ai_allowance_version") != 1
                or before.get("status") != "active" or before.get("entitlement_version") not in (None, 2)):
            errors.append(f"Active separate AI allowances required: {identity}"); continue
        pending = account.get("resource_quota_pending", {})
        if not isinstance(pending, dict) or any(not isinstance(value, int) or isinstance(value, bool) or value != 0 for value in pending.values()):
            errors.append(f"Reconcile pending resource reservations: {identity}"); continue
        usage = before.get("usage", {})
        required = ("projects_used", "stories_used", "scenarios_used", "testcases_used", "team_members_used",
            "managed_ai_credits_used", "byok_ai_requests_used", "testcases_basic_used", "testcases_medium_used", "testcases_advanced_used")
        if not isinstance(usage, dict) or any(key not in usage for key in required):
            errors.append(f"Reconcile missing usage counters: {identity}"); continue
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in usage.values()):
            errors.append(f"Reconcile invalid usage: {identity}"); continue
        if any(usage.get(key, 0) < value for key, value in (inventory or {}).get(identity, {}).items()):
            errors.append(f"Reconcile under-counted resource/seat inventory before adoption: {identity}"); continue
        try:
            limits = entitlement_limits(before, target)
        except ValueError as error:
            errors.append(f"{identity}: {error}"); continue
        after = {**deepcopy(before), "plan": target, "limits": limits,
            "entitlement_version": 2, "testcase_complexity_policy": "SHARED_TOTAL"}
        if after == before:
            continue
        over = {key: usage.get(key.replace("_limit", "_used"), 0) for key, limit in limits.items()
            if limit is not None and usage.get(key.replace("_limit", "_used"), 0) > limit
            and key not in ("ai_gen_limit", "executions_limit")}
        changes.append({"account_id": identity,
            "before": {"subscription": before, "resource_quota_pending": deepcopy(pending),
                "owner_user_id": account.get("owner_user_id"), "billing_version": 1, "status": "ACTIVE"},
            "after": after, "over_capacity": over})
    plan = {"schema_version": "account-entitlements-v2", "changes": changes, "errors": errors, "inventory": inventory or {}}
    return {**plan, "plan_digest": fingerprint(plan)}


async def apply_entitlements(database, plan, expected_digest, *, maintenance_confirmed=False):
    unsigned = {key: value for key, value in plan.items() if key != "plan_digest"}
    if (not maintenance_confirmed or plan.get("schema_version") != "account-entitlements-v2"
            or plan.get("errors") or expected_digest != plan.get("plan_digest")
            or fingerprint(unsigned) != expected_digest):
        raise ValueError("Matching conflict-free reviewed plan and stopped writers are required.")
    quota = ResourceQuota(database)
    for change in plan["changes"]:
        async def work(session):
            identity = change["account_id"]
            receipt_id = fingerprint([identity, expected_digest])
            if await database["account_entitlement_receipts"].find_one({"_id": receipt_id}, session=session):
                return  # A committed acknowledgement may have been lost. Never rewrite newer state.
            if await database["ai_usage_records"].count_documents({"account_id": identity, "status": "STARTED"}, session=session):
                raise ValueError("Reconcile active or uncertain AI work before changing policy.")
            if await database["resource_quota_reservations"].count_documents(
                    {"owner_collection": "customer_accounts", "owner_id": identity, "state": "RESERVED"}, session=session):
                raise ValueError("Settle resource reservations before changing policy.")
            before = change["before"]
            counts = await inventory_counts(database, {"_id": identity, "owner_user_id": before["owner_user_id"]}, session=session)
            if any(before["subscription"]["usage"].get(key, 0) < value for key, value in counts.items()):
                raise ValueError("Resource/seat inventory exceeds reviewed counters. Reconcile before adoption.")
            # Missing and empty pending maps are equivalent; every nonzero pending field is rejected.
            query = {"_id": identity, **{key: value for key, value in before.items() if key != "resource_quota_pending"},
                "$or": [{"resource_quota_pending": before["resource_quota_pending"]}, {"resource_quota_pending": {"$exists": False}}]}
            result = await database["customer_accounts"].update_one(query,
                {"$set": {"subscription": change["after"]}}, session=session)
            if result.matched_count != 1:
                raise ValueError("Account changed; stop and generate a new reviewed plan.")
            await database["account_entitlement_receipts"].insert_one({"_id": receipt_id,
                "account_id": identity, "plan_digest": expected_digest, "before": before["subscription"],
                "after": change["after"], "at": datetime.now(timezone.utc)}, session=session)
        await quota.transaction(work)
