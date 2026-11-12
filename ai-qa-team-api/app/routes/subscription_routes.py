from fastapi import APIRouter, Depends, HTTPException
from app.utils.auth_dependency import get_current_user
from app.services.subscription_services import get_subscription
from app.models.subscription import Subscription
from app.db.connection import db
from app.app_config.plan_limits import PLAN_LIMITS
from fastapi import Request
import json

router = APIRouter(prefix="/auth", tags=["Subscription"])

@router.patch("/auth/upgrade-plan")
async def upgrade_plan(plan: str, current_user=Depends(get_current_user)):
    from app.services.account_billing import billing_account
    from app.services.customer_accounts import CustomerAccounts
    account = await billing_account(db, current_user)
    if account:
        await CustomerAccounts(db).admin(current_user)
        if current_user.get("platform_role") not in ("OWNER", "ADMIN"):
            raise HTTPException(403, "Plan changes require a verified billing or platform administration operation.")
        from app.services.subscription_services import upgrade_plan as change_plan
        sub = await change_plan(current_user["email"], plan)
        return {"message": "Account plan updated.", "subscription": sub}
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
async def check_plan(request: Request, current_user=Depends(get_current_user)):

    user_id = (
        current_user.get("_id") or 
        current_user.get("id") or 
        current_user.get("email")
    )

    subscription = await get_subscription(user_id)

    if not subscription:
        # Auto-heal free subscription
        sub = Subscription().model_dump()
        await db["users"].update_one(
            {"$or": [{"_id": user_id}, {"email": user_id}]},
            {"$set": {"subscription": sub}},
        )
        subscription = sub

    return {"subscription": subscription}

@router.get("/plans")
async def list_plans():
    return [{"name": k, **v} for k, v in PLAN_LIMITS.items()]
