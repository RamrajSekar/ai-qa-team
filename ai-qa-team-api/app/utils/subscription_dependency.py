from fastapi import Depends, HTTPException, status
from app.utils.auth_dependency import get_current_user
from app.services.subscription_services import get_subscription, increment_usage
from datetime import datetime, timezone
import logging
from app.db.connection import db


logger = logging.getLogger(__name__)

def subscription_required(resource_type: str):
    """
    Returns a dependency function bound to a specific action
    (stories/scenarios/executions)
    """
    async def _dependency(current_user=Depends(get_current_user)):
        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")
        sub = await get_subscription(user_id)

        if not sub:
            logger.error(f"❌ No subscription found for {user_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active subscription.")

        plan = sub.get("plan", "free")
        usage = sub.get("usage", {})
        limits = sub.get("limits", {})

        field_map = {
            "stories": ("stories_used", "stories_limit"),
            "scenarios": ("scenarios_used", "scenarios_limit"),
            "executions": ("executions_used", "executions_limit"),
            "team_members": ("team_members_used", "team_members_limit"),
        }
        used_field, limit_field = field_map[resource_type]
        used = usage.get(used_field, 0)
        limit = limits.get(limit_field, 0)

        logger.info(f"🔢 {user_id} plan={plan} usage={used}/{limit} for {resource_type}")
        # Free/Pro plans only limited by numeric limits
        if limit is not None and used >= limit:
            logger.warning(f"🚫 {user_id} reached {resource_type} limit ({used}/{limit})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{resource_type.capitalize()} limit reached. Please upgrade your plan."
            )

        # ✅ Passed → increment usage
        await increment_usage(user_id, used_field)
        logger.info(f"✅ Allowed {resource_type} operation for {user_id}")
        return current_user
    return _dependency