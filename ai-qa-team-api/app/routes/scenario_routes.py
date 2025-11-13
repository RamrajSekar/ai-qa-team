from fastapi import APIRouter, HTTPException, Depends
from app.db.connection import db
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

@router.post("/")
async def create_scenario(
    scenario_data: dict, 
    current_user=Depends(get_current_user), 
    _: None = Depends(subscription_required("stories"))
    ):
    return {
        "message": "Scenario created successfully.",
        "plan": current_user["subscription"]["plan"]
    }

@router.get("/")
async def get_scenarios(scenario_data: dict, current_user=Depends(get_current_user)):
    return {
        "message": f"Scenarios visible to {current_user['email']}",
        "plan": current_user["subscription"]["plan"]
    }