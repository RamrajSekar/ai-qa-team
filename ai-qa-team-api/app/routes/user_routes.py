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
