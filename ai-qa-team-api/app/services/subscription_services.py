from datetime import datetime
from app.models.subscription import Subscription
from app.db.connection import db
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

async def upgrade_plan(user_id: str, new_plan: str, provider: str = "manual"):
    """Upgrade a user's plan and persist it in MongoDB."""
    new_subscription = Subscription().upgrade_to(new_plan)
    new_subscription.provider = provider
    # Try updating by _id; if no match, fallback to email
    result = await db["users"].update_one(
        {"$or": [{"_id": user_id}, {"email": user_id}]},
        {"$set": {"subscription": new_subscription.model_dump()}}
    )

    if result.modified_count == 0:
        raise Exception("No user record updated. Check user_id or email mapping.")

    return new_subscription

async def get_subscription(user_identifier: str):
    logger.info(f"Checking subscription for user: {user_identifier}")
    user = await db["users"].find_one(
        {"$or": [{"_id": user_identifier}, {"id": user_identifier}, {"email": user_identifier}]},
        {"subscription": 1}
    )
    if not user:
        logger.warning(f"User not found for {user_identifier}")
        return None

    sub = user.get("subscription")
    if not sub:
        logger.warning(f"No subscription field for {user_identifier}")
        return None

    # Heal structure if needed
    healed = False
    if "usage" not in sub or not isinstance(sub["usage"], dict):
        sub["usage"] = {"stories_used": 0, "scenarios_used": 0, "executions_used": 0}
        healed = True
    if "limits" not in sub or not isinstance(sub["limits"], dict):
        sub["limits"] = {"stories_limit": 5, "scenarios_limit": 10, "executions_limit": 20}
        healed = True

    if healed:
        await db["users"].update_one(
            {"$or": [{"_id": user_identifier}, {"id": user_identifier}, {"email": user_identifier}]},
            {"$set": {"subscription": sub}}
        )
        logger.info(f"Healed subscription fields for {user_identifier}")

    logger.info(f"Subscription fetched for {user_identifier}: {sub.get('plan', 'unknown')}")
    return sub

async def increment_usage(user_identifier: str, field: str):
    """
    Safely increment a usage field (stories_used, scenarios_used, executions_used)
    and log the result.
    """
    valid_fields = ["stories_used", "scenarios_used", "executions_used"]
    if field not in valid_fields:
        logger.warning(f"Invalid usage field '{field}' for {user_identifier}")
        return

    result = await db["users"].update_one(
        {"$or": [{"_id": user_identifier}, {"id": user_identifier}, {"email": user_identifier}]},
        {"$inc": {f"subscription.usage.{field}": 1}}
    )

    if result.modified_count:
        logger.info(f"Incremented {field} for {user_identifier}")
    else:
        logger.warning(f"Failed to increment {field} for {user_identifier}")
