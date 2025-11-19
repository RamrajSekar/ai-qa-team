from fastapi import APIRouter, HTTPException, Depends, Query, status
from app.db.connection import db
from app.models.scenario_model import ScenarioCreate, ScenarioUpdate, ScenarioResponse, StepModel, ScenarioGenerationResponse, ScenarioGenerationSummary
from app.routes.auth_routes import get_current_user
from app.utils.subscription_dependency import subscription_required
from bson.objectid import ObjectId
from app.services.story_service import get_next_sequence
from app.services.subscription_services import get_subscription
from datetime import datetime, timezone
from app.services.ai.scenario_generator import generate_scenarios_from_story
from app.services.subscription_services import increment_usage
from typing import List
from app.ai.scenario_prompts import build_scenario_prompt

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


# -------------------------------------------------------------------
# Helper: normalize a Mongo scenario document into ScenarioResponse
# -------------------------------------------------------------------
def normalize_step(raw, idx):
    """
    Normalize ANY AI or DB step into a valid StepModel-compatible dict.
    """

    # Case 1 — already a correct dict
    if isinstance(raw, dict):
        return {
            "step_id": raw.get("step_id", f"STEP{idx:03d}"),
            "category": raw.get("category", "General"),
            "action": raw.get("action", "Undefined action"),
            "expected": raw.get("expected", "No expected result")
        }

    # Case 2 — raw string
    if isinstance(raw, str):
        return {
            "step_id": f"STEP{idx:03d}",
            "category": "General",
            "action": raw,
            "expected": "Expected result not provided"
        }

    # Case 3 — list of strings
    if isinstance(raw, list):
        return {
            "step_id": f"STEP{idx:03d}",
            "category": "General",
            "action": " → ".join(str(x) for x in raw),
            "expected": "Expected result not provided"
        }

    # Fallback
    return {
        "step_id": f"STEP{idx:03d}",
        "category": "General",
        "action": str(raw),
        "expected": "Expected result not provided"
    }


def _build_scenario_response(doc):
    raw_steps = doc.get("steps", [])

    normalized_steps = [
        normalize_step(step_raw, idx)
        for idx, step_raw in enumerate(raw_steps, start=1)
    ]

    return ScenarioResponse(
        scenario_id=doc["scenario_id"],
        story_id=doc["story_id"],
        project_id=doc["project_id"],
        title=doc["title"],
        description=doc.get("description", ""),
        steps=normalized_steps,
        status=doc.get("status", "pending"),
        created_by=doc.get("created_by", ""),
        created_at=doc.get("created_at", ""),
        generated_by_agent=str(doc.get("generated_by_agent")) if doc.get("generated_by_agent") else None
    )


# -------------------------------------------------------------------
# 1. CREATE SCENARIO (manual)
# -------------------------------------------------------------------
@router.post("/", response_model=ScenarioResponse)
async def create_scenario(
    scenario: ScenarioCreate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    """
    Manually create a scenario for a story.

    Assumptions:
    - scenario.story_id is the BUSINESS story_id (e.g. ST001), not the Mongo _id.
    - The story must exist and belong to the current user (or their project).
    """
    try:
        user_email = current_user.get("email")

        # Verify story exists and is accessible
        story = await db["stories"].find_one(
            {"story_id": scenario.story_id, "created_by": user_email}
        )
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or access denied.",
            )

        # Generate sequential scenario ID like SC001
        new_scenario_id = await get_next_sequence("scenario_id", "SC")
        agent_name = story.get("agent_identities", {}).get(
            "scenario_builder", "Scenario Builder"
        )
        scenario_doc = {
            "scenario_id": new_scenario_id,
            "story_id": scenario.story_id,              # business story id (e.g. ST001)
            "project_id": story.get("project_id"),      # optional but useful for queries
            "title": scenario.title,
            "description": scenario.description,
            "steps": scenario.steps or [],
            "status": "pending",
            "generated_by_agent": agent_name,
            "created_by": user_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = await db["scenarios"].insert_one(scenario_doc)
        scenario_doc["_id"] = result.inserted_id

        return _build_scenario_response(scenario_doc)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create scenario: {str(e)}",
        )

# -------------------------------------------------------------------
# 2. LIST SCENARIOS for a story
# -------------------------------------------------------------------
@router.get("/", response_model=List[ScenarioResponse])
async def list_scenarios(
    story_id: str = Query(..., description="Business story_id, e.g. ST001"),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    """
    List scenarios linked to a given story_id (business ID, ST001, ST002, ...).
    """
    user_email = current_user.get("email")

    # Optional: enforce that the story belongs to this user
    story = await db["stories"].find_one(
        {"story_id": story_id, "created_by": user_email}
    )
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found or access denied.",
        )

    cursor = db["scenarios"].find({"story_id": story_id})
    scenarios: List[ScenarioResponse] = []

    async for doc in cursor:
        scenarios.append(_build_scenario_response(doc))

    return scenarios

# -------------------------------------------------------------------
# 3. GET SINGLE SCENARIO by scenario_id (e.g. SC001)
# -------------------------------------------------------------------
@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    """
    Fetch a single scenario by its business id (scenario_id like SC001).
    """
    user_email = current_user.get("email")

    doc = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": user_email}
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found or access denied.",
        )

    return _build_scenario_response(doc)

# -------------------------------------------------------------------
# 4. UPDATE SCENARIO by scenario_id
# -------------------------------------------------------------------
@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    update: ScenarioUpdate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    """
    Update a scenario using its business id (scenario_id, e.g. SC001).
    """
    user_email = current_user.get("email")

    update_data = {
        k: v for k, v in update.model_dump().items() if v is not None
    }

    result = await db["scenarios"].update_one(
        {"scenario_id": scenario_id, "created_by": user_email},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found or access denied.",
        )

    updated = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": user_email}
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch updated scenario.",
        )

    return _build_scenario_response(updated)



# -------------------------------------------------------------------
# 5. DELETE SCENARIO by scenario_id
# -------------------------------------------------------------------
@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    """
    Delete a scenario using its business id (scenario_id, e.g. SC001).
    """
    user_email = current_user.get("email")

    result = await db["scenarios"].delete_one(
        {"scenario_id": scenario_id, "created_by": user_email}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found or access denied.",
        )
    return {"message": "Scenario deleted successfully"}

# -------------------------------------------------------------------
# 6. AI SCENARIO GENERATION from Story
# -------------------------------------------------------------------
@router.post("/generate-from-story", response_model=ScenarioGenerationResponse)
async def generate_scenarios_for_story(
    story_id: str = Query(..., description="Business story_id, e.g. S001"),
    count: int = Query(3, ge=1, le=20),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("ai_generation")),
):
    """
    Option A+ model:
    - Never errors on limits
    - If user requests more than allowed, auto-adjust downward
    - If user has 0 remaining, return empty scenario list with friendly upgrade message
    """

    try:
        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")
        user_email = current_user.get("email")

        # ------------------------------------------------------
        # 1️⃣ LOAD STORY
        # ------------------------------------------------------
        story = await db["stories"].find_one({"story_id": story_id, "created_by": user_email})
        if not story:
            raise HTTPException(404, "Story not found or access denied.")

        # ------------------------------------------------------
        # 2️⃣ SUBSCRIPTION LIMITS
        # ------------------------------------------------------
        sub = await get_subscription(user_id)

        # Global scenario limits
        total_existing = await db["scenarios"].count_documents({"created_by": user_email})
        max_scenarios = sub["limits"].get("scenarios_limit", None)
        remaining_scenarios = (
            max_scenarios - total_existing if max_scenarios is not None else None
        )

        # AI generation limits
        used_ai = sub["usage"].get("ai_gen_used", 0)
        ai_limit = sub["limits"].get("ai_gen_limit", None)
        remaining_ai = (
            ai_limit - used_ai if ai_limit is not None else None
        )

        # ------------------------------------------------------
        # 3️⃣ DETERMINE ALLOWABLE GENERATION COUNT (A+ logic)
        # ------------------------------------------------------
        # Default = user requested count
        allowed_count = count

        # Apply AI generation limit
        if remaining_ai is not None:
            allowed_count = min(allowed_count, remaining_ai)

        # Apply scenario limit
        if remaining_scenarios is not None:
            allowed_count = min(allowed_count, remaining_scenarios)

        # ----------------------------------------
        # If ZERO allowed → return upgrade message
        # ----------------------------------------
        if allowed_count <= 0:
            return ScenarioGenerationResponse(
                scenarios=[],
                summary=ScenarioGenerationSummary(
                    message="No AI generations left for your plan.",
                    remaining_ai_generations=remaining_ai,
                    remaining_scenario_slots=remaining_scenarios,
                    plan=sub["plan"],
                )
            )

        # ------------------------------------------------------
        # 4️⃣ FETCH PROJECT → AGENT IDENTITY
        # ------------------------------------------------------
        project = await db["projects"].find_one({"project_id": story["project_id"]})
        if not project:
            raise HTTPException(404, "Project not found. Please create a project first.")

        agent_name = project.get("agent_identities", {}).get("scenario_builder", "Scenario Builder")

        # ------------------------------------------------------
        # 5️⃣ BUILD PROMPT USING TEMPLATE
        # ------------------------------------------------------
        prompt = build_scenario_prompt(agent_name, story, allowed_count)

        # ------------------------------------------------------
        # 6️⃣ CALL AI GENERATOR
        # ------------------------------------------------------
        ai_result = await generate_scenarios_from_story(prompt)

        if not isinstance(ai_result, list):
            raise HTTPException(500, "AI generator returned invalid data.")

        created_docs = []

        # ------------------------------------------------------
        # 7️⃣ SAVE EACH SCENARIO (ONLY allowed_count)
        # ------------------------------------------------------
        ai_result = ai_result[:allowed_count]  # trim extra just in case

        for i, scenario in enumerate(ai_result, start=1):

            scenario_id = await get_next_sequence("scenario_id", "SC")

            raw_steps = scenario.get("steps", [])
            normalized_steps = []

            for idx, step in enumerate(raw_steps, start=1):
                normalized_steps.append({
                    "step_id": f"STEP{idx:03d}",
                    "category": step.get("category", "General"),
                    "action": step.get("action", ""),
                    "expected": step.get("expected", ""),
                })

            doc = {
                "scenario_id": scenario_id,
                "story_id": story_id,
                "project_id": story["project_id"],
                "title": scenario["title"],
                "description": scenario.get("description", ""),
                "steps": normalized_steps,
                "status": "pending",
                "created_by": user_email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "generated_by_agent": agent_name,
            }

            result = await db["scenarios"].insert_one(doc)
            doc["_id"] = result.inserted_id
            created_docs.append(_build_scenario_response(doc))

            await increment_usage(user_id, "ai_gen_used")
            await increment_usage(user_id, "scenarios_used")

        # ------------------------------------------------------
        # 8️⃣ SUCCESS SUMMARY
        # ------------------------------------------------------
        new_remaining_ai = (
            remaining_ai - allowed_count if remaining_ai is not None else "unlimited"
        )

        new_remaining_slots = (
            remaining_scenarios - allowed_count if remaining_scenarios is not None else "unlimited"
        )

        return ScenarioGenerationResponse(
            scenarios=created_docs,
            summary=ScenarioGenerationSummary(
                message=f"{allowed_count} scenarios generated successfully by agent '{agent_name}'.",
                remaining_ai_generations=new_remaining_ai,
                remaining_scenario_slots=new_remaining_slots,
                plan=sub["plan"]
            )
        )

    except Exception as e:
        import traceback
        print("\n\n🔥 DEBUG ERROR 🔥")
        traceback.print_exc()
        raise HTTPException(500, str(e))
