"""Explicit, narrow update for migrated Free accounts; no usage reset."""
from app.services.approved_visual_run import digest


def plan_free_allowance(accounts):
    changes = [{"account_id": account["_id"], "old_limit": 1, "new_limit": 2}
               for account in accounts if account.get("billing_version") == 1
               and account.get("subscription", {}).get("plan") == "free"
               and account.get("subscription", {}).get("limits", {}).get("team_members_limit") == 1]
    return {"changes": changes, "plan_digest": digest(changes)}


async def apply_free_allowance(database, plan, expected_digest):
    if expected_digest != plan["plan_digest"]:
        raise ValueError("A matching reviewed allowance plan is required.")
    for change in plan["changes"]:
        result = await database["customer_accounts"].update_one(
            {"_id": change["account_id"], "billing_version": 1, "subscription.plan": "free", "subscription.limits.team_members_limit": 1},
            {"$set": {"subscription.limits.team_members_limit": 2}})
        if result.matched_count != 1:
            raise ValueError("Account allowance changed. Stop and generate a new dry run.")
