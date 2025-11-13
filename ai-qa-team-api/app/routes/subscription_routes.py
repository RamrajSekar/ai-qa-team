from fastapi import APIRouter, Depends, HTTPException
from app.utils.auth_dependency import get_current_user
from app.services.subscription_services import get_subscription
from app.models.subscription import Subscription
from app.db.connection import db
from app.app_config.plan_limits import PLAN_LIMITS
import json

router = APIRouter(prefix="/auth", tags=["Subscription"])

@router.patch("/auth/upgrade-plan")
async def upgrade_plan(plan: str, current_user=Depends(get_current_user)):
    user_id = current_user.get("_id") or current_user.get("email")
    if plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid plan name: {plan}")

    sub = Subscription(plan=plan)
    sub.apply_plan_defaults()

    await db["users"].update_one(
        {"_id": user_id},
        {"$set": {"subscription": sub.model_dump()}}
    )
    return {
        "message": f"Upgraded to {plan} plan successfully.",
        "subscription": json.loads(sub.model_dump_json())
    }

@router.get("/check-plan")
async def check_plan(current_user=Depends(get_current_user)):
    user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")
    subscription = await get_subscription(user_id)
    print("current_user in /check-plan:", current_user)
    if not subscription:
       # Auto-heal case: attach free subscription if missing
        sub = Subscription().model_dump()
        await db["users"].update_one(
            {"$or": [{"_id": user_id}, {"email": user_id}]},
            {"$set": {"subscription": sub}}
        )
        subscription = sub
    return {"subscription": subscription}

    @router.get("/plans")
    async def list_plans():
        return [{"name": k, **v} for k, v in PLAN_LIMITS.items()]