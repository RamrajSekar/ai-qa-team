from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal

from app.db.connection import db
from app.utils.auth_dependency import get_current_user  # your existing auth dep
from app.services.onboarding_services import (
    get_onboarding_status,
    update_onboarding_step,
)

router = APIRouter(
    prefix='/onboarding',
    tags=['Onboarding'],
)

class OnboardingStepUpdate(BaseModel):
    step: int
    status: Literal['not_started', 'in_progress', 'completed'] = 'in_progress'

@router.get('/status')
async def onboarding_status(current_user=Depends(get_current_user)):
    user_id = str(current_user['_id'])
    status = await get_onboarding_status(user_id)
    return {'onboarding': status}

@router.post('/step')
async def onboarding_step(
    payload: OnboardingStepUpdate,
    current_user=Depends(get_current_user),
):
    # simple bounds
    if payload.step < 1 or payload.step > 6:
        raise HTTPException(400, 'Invalid step')

    user_id = str(current_user['_id'])
    await update_onboarding_step(user_id, payload.step, payload.status)
    return {'ok': True}


@router.put("/progress")
async def update_onboarding(data: dict, current_user=Depends(get_current_user)):
    email = current_user["email"]

    update_data = {}

    if "current_step" in data:
        update_data["onboarding.current_step"] = data["current_step"]

    if "step_key" in data:
        step = data["step_key"]
        update_data[f"onboarding.steps.{step}"] = True
        update_data["onboarding.onboarding_status"] = "in_progress"

    if "project_id" in data:
        update_data["onboarding.context.project_id"] = data["project_id"]

    if "environment_id" in data:
        update_data["onboarding.context.environment_id"] = data["environment_id"]

    await db["users"].update_one({"email": email}, {"$set": update_data})
    return {"success": True}



@router.post("/finish")
async def finish_onboarding(current_user=Depends(get_current_user)):
    await db["users"].update_one(
        {"email": current_user["email"]},
        {"$set": {
            "onboarding.onboarding_status": "completed",
            "onboarding.current_step": 99,
            "onboarding.steps.finish": True,
        }}
    )
    return {"success": True}
