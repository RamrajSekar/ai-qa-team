"""Customer-level billing routing. No user fallback after account cutover."""
from copy import deepcopy
from fastapi import HTTPException
from app.config import settings


async def billing_account(database, user):
    if not user or not user.get("account_id"):
        if settings.features.account_subscriptions:
            raise HTTPException(409, "Customer account migration is required before shared billing.")
        return None
    account = await database["customer_accounts"].find_one({"_id": user["account_id"]})
    if not settings.features.account_subscriptions and not (account or {}).get("billing_version"):
        return None
    if user.get("account_state") != "ACTIVE" or not account or account.get("status") != "ACTIVE":
        raise HTTPException(403, "Customer account is unavailable.")
    if account.get("billing_version") != 1 or not isinstance(account.get("subscription"), dict):
        raise HTTPException(409, "Customer account subscription migration is required.")
    return account


def initial_subscription(subscription):
    from app.models.subscription import Subscription
    if not subscription:
        model = Subscription(); model.apply_plan_defaults(); subscription = model.model_dump()
    result = deepcopy(subscription)
    # A newly created account has no additional members or pending invites.
    result.setdefault("usage", {})["team_members_used"] = 0
    if settings.features.separate_ai_allowances:
        from app.services.ai_allowances import initialize_allowances
        initialize_allowances(result)
    if settings.features.billing_checkout and settings.features.separate_ai_allowances:
        result.update(entitlement_version=2, testcase_complexity_policy="SHARED_TOTAL")
    return result


async def change_seats(database, account, delta):
    """Additional account users + pending/claimed invites, never project assignments."""
    query = {"_id": account["_id"], "billing_version": 1, "status": "ACTIVE"}
    if delta > 0:
        from app.services.billing.access import require_consumption
        require_consumption(account)
        if account.get("billing", {}).get("managed_spend_required"):
            query["billing"] = account["billing"]
        query["subscription.status"] = "active"
        if account["subscription"].get("status") != "active":
            raise HTTPException(403, "No active account subscription.")
        limit = account["subscription"].get("limits", {}).get("team_members_limit", 0)
        query["subscription.limits.team_members_limit"] = limit
        if limit is not None:
            query["subscription.usage.team_members_used"] = {"$lt": limit}
    else:
        query["subscription.usage.team_members_used"] = {"$gt": 0}
    result = await database["customer_accounts"].update_one(query, {"$inc": {"subscription.usage.team_members_used": delta}})
    if delta > 0 and result.modified_count != 1:
        raise HTTPException(403, "Account member allowance reached.")


async def scenario_complexity_usage(database, account_id):
    """Read-only inventory breakdown; subscription reservations remain untouched."""
    rows = await database["projects"].aggregate([
        {"$match": {"account_id": account_id}},
        {"$lookup": {"from": "scenarios", "let": {"project": "$project_id"}, "pipeline": [
            {"$match": {"$expr": {"$eq": ["$project_id", "$$project"]}}},
            {"$group": {"_id": {"$cond": [
                {"$in": ["$complexity", ["basic", "medium", "advanced"]]},
                "$complexity", "unspecified"]}, "count": {"$sum": 1}}},
        ], "as": "complexity_counts"}},
        {"$unwind": "$complexity_counts"},
        {"$group": {"_id": "$complexity_counts._id", "count": {"$sum": "$complexity_counts.count"}}},
    ]).to_list(4)
    return {f"scenarios_{tier}_used": next((row["count"] for row in rows if row["_id"] == tier), 0)
            for tier in ("basic", "medium", "advanced", "unspecified")}
