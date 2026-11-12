from datetime import datetime
from app.models.subscription import Subscription
from app.db.connection import db
from fastapi import HTTPException, status
import logging
from app.app_config.plan_limits import PLAN_LIMITS
from bson import ObjectId
from copy import deepcopy
from app.services.account_billing import billing_account


async def account_target(user_identifier):
    user = await db["users"].find_one(build_user_query(user_identifier))
    account = await billing_account(db, user)
    return account

logger = logging.getLogger(__name__)

def build_user_query(user_identifier: str):
    return {
        "$or": [
            {"_id": ObjectId(user_identifier)} if ObjectId.is_valid(user_identifier) else {"_id": None},
            {"id": user_identifier},
            {"email": user_identifier}
        ]
    }

async def upgrade_plan(user_id: str, new_plan: str, provider: str = "manual"):
    """Upgrade a user's plan and persist it in MongoDB."""
    if new_plan not in PLAN_LIMITS:
        raise HTTPException(400, "Invalid plan.")
    account = await account_target(user_id)
    model = Subscription(plan=new_plan); model.apply_plan_defaults()
    new_subscription = model
    new_subscription.provider = provider
    # Try updating by _id; if no match, fallback to email
    if account:
        # Entitlement changes preserve metered usage and period, never refill credits.
        await db["customer_accounts"].update_one({"_id": account["_id"], "billing_version": 1},
            {"$set": {"subscription.plan": new_plan, "subscription.limits": model.limits.model_dump(), "subscription.provider": provider}})
        return {**account["subscription"], "plan": new_plan, "limits": model.limits.model_dump(), "provider": provider}
    result = await db["users"].update_one(
        {"$or": [{"_id": user_id}, {"email": user_id}]},
        {"$set": {"subscription": new_subscription.model_dump()}}
    )

    if result.modified_count == 0:
        raise Exception("No user record updated. Check user_id or email mapping.")

    return new_subscription

async def get_subscription(user_identifier: str):
    account = await account_target(user_identifier)
    if account:
        return {**deepcopy(account["subscription"]), "billing_scope": "ACCOUNT", "account_id": account["_id"]}
    logger.info(f"Checking subscription for user: {user_identifier}")
    query = build_user_query(user_identifier)
    user = await db["users"].find_one(query, {"subscription": 1})
    if not user:
        logger.warning(f"User not found for {user_identifier}")
        return None

    sub = user.get("subscription")
    if not sub:
        logger.warning(f"No subscription field for {user_identifier}")
        return None

    healed = False

    # ---------- Heal USAGE ----------
    default_usage = {
        "projects_used": 0,
        "stories_used": 0,
        "scenarios_used": 0,
        "executions_used": 0,
        "team_members_used": 0,
        "ai_gen_used": 0,
    }

    if "usage" not in sub or not isinstance(sub["usage"], dict):
        sub["usage"] = default_usage
        healed = True
    else:
        # Add missing usage fields
        for k, v in default_usage.items():
            if k not in sub["usage"]:
                sub["usage"][k] = v
                healed = True

    # ---------- Heal LIMITS ----------
    default_limits = PLAN_LIMITS.get(sub.get("plan", "free"))

    if "limits" not in sub or not isinstance(sub["limits"], dict):
        sub["limits"] = default_limits
        healed = True
    else:
        # Add missing limit fields
        for k, v in default_limits.items():
            if k not in sub["limits"]:
                sub["limits"][k] = v
                healed = True

    # ---------- Save healed subscription ----------
    if healed:
        await db["users"].update_one(
            {"$or": [{"_id": user_identifier}, {"id": user_identifier}, {"email": user_identifier}]},
            {"$set": {"subscription": sub}}
        )
        logger.info(f"🔧 Healed subscription fields for {user_identifier}")

    logger.info(f"Subscription fetched for {user_identifier}: {sub.get('plan', 'unknown')}")
    return sub


async def increment_usage(user_identifier: str, field: str):
    """
    Safely increment a usage field (projects_used, stories_used, scenarios_used, executions_used)
    and log the result.
    """
    query = build_user_query(user_identifier)
    valid_fields = ["projects_used", "stories_used", "scenarios_used", "testcases_used",
                    "executions_used", "team_members_used", "ai_gen_used", "testcases_basic_used", "testcases_medium_used", "testcases_advanced_used"]
    if field not in valid_fields:
        logger.warning(f"Invalid usage field '{field}' for {user_identifier}")
        return

    account = await account_target(user_identifier)
    if account:
        await db["customer_accounts"].update_one({"_id": account["_id"], "billing_version": 1},
            {"$inc": {f"subscription.usage.{field}": 1}})
        return

    result = await db["users"].update_one(
        query,
        {"$inc": {f"subscription.usage.{field}": 1}},
        
    )

    if result.modified_count:
        logger.info(f"Incremented {field} for {user_identifier}")
    else:
        logger.warning(f"Failed to increment {field} for {user_identifier}")


async def decrement_usage(user_email: str, field: str):
    if field not in {"projects_used", "stories_used", "scenarios_used", "testcases_used", "executions_used", "team_members_used", "ai_gen_used", "testcases_basic_used", "testcases_medium_used", "testcases_advanced_used"}:
        raise HTTPException(400, "Invalid usage field.")
    account = await account_target(user_email)
    if account:
        await db["customer_accounts"].update_one({"_id": account["_id"], f"subscription.usage.{field}": {"$gt": 0}},
            {"$inc": {f"subscription.usage.{field}": -1}})
        return
    await db["users"].update_one(
        {"email": user_email},
        {"$inc": {f"subscription.usage.{field}": -1}}
    )

    # Ensure it does not go negative
    await db["users"].update_one(
        {"email": user_email, f"subscription.usage.{field}": {"$lt": 0}},
        {"$set": {f"subscription.usage.{field}": 0}}
    )
