"""Reviewed billing cutover. Legacy user subscriptions remain unchanged."""
from copy import deepcopy
from datetime import datetime, timezone
from app.app_config.plan_limits import PLAN_LIMITS
from app.models.subscription import UsageModel
from app.services.approved_visual_run import digest


def plan_subscriptions(accounts, users, projects, counts, invitations, mapping=None, *, now=None):
    now = now or datetime.now(timezone.utc)
    period = datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()
    choices = (mapping or {}).get("subscription_sources", {})
    errors, changes = [], []
    for account in accounts:
        if account.get("billing_version") == 1:
            continue  # Never reset or recopy an account already cut over.
        identity = account["_id"]
        members = [user for user in users if user.get("account_id") == identity]
        source_id = choices.get(identity, account.get("owner_user_id"))
        source = next((user for user in members if str(user["_id"]) == source_id), None)
        if not source or not isinstance(source.get("subscription"), dict):
            errors.append("Missing reviewed subscription source: " + identity); continue
        subscription = deepcopy(source["subscription"])
        if subscription.get("plan") not in PLAN_LIMITS or not isinstance(subscription.get("limits"), dict):
            errors.append("Invalid source subscription: " + identity); continue
        paid = {user.get("subscription", {}).get("plan") for user in members if user.get("subscription", {}).get("plan") not in (None, "free")}
        if paid and identity not in choices and paid != {subscription["plan"]}:
            errors.append("Review conflicting paid subscriptions and select a source: " + identity); continue
        usage = UsageModel().model_dump()
        for user in members:
            for key, value in user.get("subscription", {}).get("usage", {}).items():
                if key not in usage:
                    continue
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    errors.append("Invalid legacy usage in account: " + identity); continue
                if key == "ai_gen_used":
                    prior = user.get("subscription", {}).get("ai_usage_period_start")
                    if prior:
                        parsed = prior if isinstance(prior, datetime) else datetime.fromisoformat(str(prior))
                        parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
                        if parsed.astimezone(timezone.utc).isoformat() != period:
                            continue  # Previous periods remain in legacy records.
                usage[key] += value
        for key, value in counts.get(identity, {}).items():
            if key in usage and key not in ("ai_gen_used", "team_members_used"):
                usage[key] = max(usage[key], value)
        # Seats are identities, not the sum of per-project membership counts.
        member_emails = {user["email"] for user in members}
        pending = {invite["_id"] for invite in invitations if invite.get("account_id") == identity and invite.get("status") in ("PENDING", "CLAIMED")}
        usage["team_members_used"] = len([user for user in members if str(user["_id"]) != account.get("owner_user_id")]) + len(pending - member_emails)
        subscription.update({"usage": usage, "ai_usage_period_start": period})
        subscription["ai_usage_period_end"] = datetime(now.year + (now.month == 12), 1 if now.month == 12 else now.month + 1, 1, tzinfo=timezone.utc).isoformat()
        changes.append({"account_id": identity, "before": {"billing_version": account.get("billing_version"), "subscription": account.get("subscription"), "owner_user_id": account.get("owner_user_id"), "status": account.get("status")},
                        "subscription": subscription, "source_user_id": source_id})
    # Include source snapshots in the private digest so usage changes invalidate review.
    plan = {"changes": changes, "errors": sorted(set(errors)), "source_digest": digest({"users": users, "projects": projects, "invitations": invitations})}
    return {**plan, "plan_digest": digest(plan)}


async def apply_subscriptions(database, plan, expected_digest, *, maintenance_confirmed=False):
    if plan["errors"] or expected_digest != plan["plan_digest"] or not maintenance_confirmed:
        raise ValueError("A matching conflict-free billing plan and stopped writers are required.")
    for change in plan["changes"]:
        result = await database["customer_accounts"].update_one({"_id": change["account_id"], **change["before"]},
            {"$set": {"subscription": change["subscription"], "billing_version": 1,
                      "billing_migration": {"source_user_id": change["source_user_id"], "plan_digest": plan["plan_digest"], "at": datetime.now(timezone.utc)}}})
        if result.matched_count != 1:
            raise ValueError("Account changed; stop and reconcile before generating a new dry run.")
