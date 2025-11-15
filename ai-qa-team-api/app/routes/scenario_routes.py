from fastapi import APIRouter, HTTPException, Depends, Query
from app.db.connection import db
from app.models.scenario_model import ScenarioCreate, ScenarioUpdate, ScenarioResponse
from app.routes.auth_routes import get_current_user
from app.utils.subscription_dependency import subscription_required
from bson.objectid import ObjectId
from app.services.story_service import get_next_sequence
from datetime import datetime, timezone
from app.services.ai.scenario_generator import generate_scenarios_from_story

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

# -------------------------
# 1. CREATE SCENARIO
# -------------------------
@router.post("/", response_model=ScenarioResponse)
async def create_scenario(
    scenario: ScenarioCreate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios"))
):
    # Generate sequential ID like SC001
    new_scenario_id = await get_next_sequence("scenario_id", "SC")
    # Verify story exists
    story = await db["stories"].find_one({"_id": ObjectId(scenario.story_id)})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")

    scenario_doc = {
        "scenario_id": new_scenario_id,
        "story_id": scenario.story_id,
        "title": scenario.title,
        "description": scenario.description,
        "steps": scenario.steps,
        "status": "pending",
        "created_by": current_user["email"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    result = await db["scenarios"].insert_one(scenario_doc)
    scenario_doc["id"] = str(result.inserted_id)

    return ScenarioResponse(**scenario_doc)

# -------------------------
# 2. LIST SCENARIOS
# -------------------------
@router.get("/", response_model=list[ScenarioResponse])
async def list_scenarios(
    story_id: str = Query(...),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios"))
):
    cursor = db["scenarios"].find({"story_id": story_id})
    scenarios = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        scenarios.append(ScenarioResponse(**doc))
    return scenarios

# -------------------------
# 3. GET SINGLE SCENARIO
# -------------------------
@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios"))
):
    doc = await db["scenarios"].find_one({"scenario_id": scenario_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Scenario not found")

    doc["id"] = str(doc["_id"])
    del doc["_id"]

    return ScenarioResponse(**doc)

# -------------------------
# 4. UPDATE SCENARIO
# -------------------------
@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    update: ScenarioUpdate,
    current_user=Depends(subscription_required("scenarios"))
):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    result = await db["scenarios"].update_one(
        {"scenario_id": scenario_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Scenario not found")

    updated = await db["scenarios"].find_one({"scenario_id": scenario_id})
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to fetch updated scenario")

    updated["id"] = str(updated["_id"])
    del updated["_id"]

    # Ensure safe defaults
    updated.setdefault("description", None)
    updated.setdefault("steps", [])
    updated.setdefault("status", "pending")

    return ScenarioResponse(**updated)



# -------------------------
# 5. DELETE SCENARIO
# -------------------------
@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    current_user=Depends(subscription_required("scenarios")),
):
    result = await db["scenarios"].delete_one({"scenario_id": scenario_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return {"message": "Scenario deleted successfully"}

@router.post("/generate-from-story/{story_id}")
async def generate_scenarios(
    story_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios"))
):
    # Fetch story
    story = await db["stories"].find_one({"_id": ObjectId(story_id)})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")

    # Call AI Generator WITH agent identity
    scenarios = await generate_scenarios_from_story(story, project_id=story["project_id"])

    return {
        "story_id": story_id,
        "generated_scenarios": scenarios
    }