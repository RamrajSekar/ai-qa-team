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
    return result


async def change_seats(database, account, delta):
    """Additional account users + pending/claimed invites, never project assignments."""
    query = {"_id": account["_id"], "billing_version": 1, "status": "ACTIVE"}
    if delta > 0:
        if account["subscription"].get("status") != "active":
            raise HTTPException(403, "No active account subscription.")
        limit = account["subscription"].get("limits", {}).get("team_members_limit", 0)
        if limit is not None:
            query["subscription.usage.team_members_used"] = {"$lt": limit}
    else:
        query["subscription.usage.team_members_used"] = {"$gt": 0}
    result = await database["customer_accounts"].update_one(query, {"$inc": {"subscription.usage.team_members_used": delta}})
    if delta > 0 and result.modified_count != 1:
        raise HTTPException(403, "Account member allowance reached.")
