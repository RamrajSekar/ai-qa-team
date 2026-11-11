from fastapi import APIRouter, Depends, HTTPException
from app.db.connection import db
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required
from bson.objectid import ObjectId
from app.services.story_service import get_next_sequence
from app.utils.feature_flags import feature_required

router = APIRouter(
    prefix="/generate-tests", tags=["Test Generator"],
    dependencies=[Depends(feature_required("test_generation"))],
)


# Purpose (Post-MVP only):
# Converts JSON → Playwright TS Code
# Used for Git export, CI/CD integration
# Advanced features only needed late
@router.post("/generate-tests")
async def generate_tests(scenario_id: str):
    scenario = await db["scenarios"].find_one({"_id": ObjectId(scenario_id)})
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    # Generate sequential ID like TC001
    test_id = await get_next_sequence("test_id", "SC")
    from app.services.test_generator import generate_playwright_test

    code = generate_playwright_test(scenario)

    return {
        "test_id": test_id,
        "scenario": scenario_id,
        "generated_code": code
    }
