from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone

from app.db.connection import db
from app.models.scenario_model import (
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioResponse,
    ScenarioGenerationResponse,
    ScenarioGenerationSummary,
)
from app.routes.auth_routes import get_current_user
from app.utils.subscription_dependency import subscription_required
from app.services.story_service import get_next_sequence
from app.services.subscription_services import get_subscription, increment_usage

from app.ai.scenario_prompts import (
    build_scenario_prompt_from_story,
    build_scenario_prompt_from_recording,
)

from app.services.ai.scenario_generator import generate_scenarios_from_prompt
from app.services.subscription_services import decrement_usage
from app.utils.feature_flags import feature_required

# ------------------------------------------------------
# Router Setup
# ------------------------------------------------------
router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


# ------------------------------------------------------
# STEP NORMALIZATION HELPERS
# ------------------------------------------------------
def normalize_step_dict(raw: dict, idx: int) -> dict:
    """
    Normalize any raw step into canonical scenario step shape:
    {
        "step_id": "STEP001",
        "category": "General",
        "action": "...",
        "expected": "..."
    }
    """

    if isinstance(raw, dict):
        return {
            "step_id": raw.get("step_id", f"STEP{idx:03d}"),
            "category": raw.get("category", "General"),
            "action": raw.get("action", raw.get("description", "Undefined action")),
            "expected": raw.get("expected", "No expected result"),
        }

    # Strings / other types fallback
    return {
        "step_id": f"STEP{idx:03d}",
        "category": "General",
        "action": str(raw),
        "expected": "No expected result",
    }


def _build_scenario_response(doc: dict) -> ScenarioResponse:
    steps_raw = doc.get("steps", []) or []

    normalized_steps = [
        normalize_step_dict(step_raw, idx)
        for idx, step_raw in enumerate(steps_raw, start=1)
    ]

    return ScenarioResponse(
        scenario_id=doc["scenario_id"],
        story_id=doc["story_id"],
        project_id=doc["project_id"],
        title=doc["title"],
        description=doc.get("description", ""),
        steps=normalized_steps,
        status=doc.get("status", "pending"),
        complexity=doc.get("complexity", ""),
        created_by=doc.get("created_by", ""),
        created_at=doc.get("created_at", ""),
        generated_by_agent=str(doc.get("generated_by_agent")) if doc.get("generated_by_agent") else None,
        # If your ScenarioResponse has this field it will be filled, otherwise ignored.
        approved=doc.get("approved", False),
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
    Manual scenario creation.
    """
    try:
        user_email = current_user["email"]

        story = await db["stories"].find_one(
            {"story_id": scenario.story_id, "created_by": user_email}
        )
        if not story:
            raise HTTPException(404, "Story not found or access denied.")

        scenario_id = await get_next_sequence("scenario_id", "SC")
        agent_name = (
            story.get("agent_identities", {})
            .get("scenario_builder", "Scenario Builder")
        )

        # Normalize incoming steps (if any)
        normalized_steps = [
            normalize_step_dict(step, idx)
            for idx, step in enumerate(scenario.steps or [], start=1)
        ]

        doc = {
            "scenario_id": scenario_id,
            "story_id": scenario.story_id,
            "project_id": story["project_id"],
            "title": scenario.title,
            "description": scenario.description,
            "steps": normalized_steps,
            "status": "pending",
            "complexity": scenario.complexity,
            "generated_by_agent": agent_name,
            "created_by": user_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            # new flag for approval flow
            "approved": False,
        }

        result = await db["scenarios"].insert_one(doc)
        doc["_id"] = result.inserted_id
        return _build_scenario_response(doc)

    except Exception as e:
        raise HTTPException(400, f"Failed to create scenario: {e}")


# -------------------------------------------------------------------
# 2. LIST SCENARIOS for a story
# -------------------------------------------------------------------
@router.get("/", response_model=List[ScenarioResponse])
async def list_scenarios(
    story_id: str = Query(...),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    user_email = current_user["email"]

    story = await db["stories"].find_one({"story_id": story_id, "created_by": user_email})
    if not story:
        raise HTTPException(404, "Story not found or access denied.")

    cursor = db["scenarios"].find({"story_id": story_id})
    results = []
    async for doc in cursor:
        results.append(_build_scenario_response(doc))
    return results


# -------------------------------------------------------------------
# 3. GET SINGLE SCENARIO
# -------------------------------------------------------------------
@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    doc = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": current_user["email"]}
    )
    if not doc:
        raise HTTPException(404, "Scenario not found.")
    return _build_scenario_response(doc)


# -------------------------------------------------------------------
# 4. UPDATE SCENARIO (includes approval + step normalization)
# -------------------------------------------------------------------
@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    update: ScenarioUpdate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    email = current_user["email"]

    existing = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": email}
    )
    if not existing:
        raise HTTPException(404, "Scenario not found or access denied.")

    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    # Preserve existing approval flag if not explicitly updated
    if "approved" not in update_data:
        update_data["approved"] = existing.get("approved", False)

    # Normalize steps if updated
    if "steps" in update_data and update_data["steps"] is not None:
        update_data["steps"] = [
            normalize_step_dict(step, idx)
            for idx, step in enumerate(update_data["steps"], start=1)
        ]

    result = await db["scenarios"].update_one(
        {"scenario_id": scenario_id, "created_by": email},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Scenario not found or access denied.")

    updated = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": email}
    )

    return _build_scenario_response(updated)


# -------------------------------------------------------------------
# 5. DELETE SCENARIO
# -------------------------------------------------------------------
# @router.delete("/{scenario_id}")
# async def delete_scenario(
#     scenario_id: str,
#     current_user=Depends(get_current_user),
#     _: None = Depends(subscription_required("scenarios")),
# ):
#     res = await db["scenarios"].delete_one(
#         {"scenario_id": scenario_id, "created_by": current_user["email"]}
#     )
#     if res.deleted_count == 0:
#         raise HTTPException(404, "Scenario not found.")
#     return {"message": "Scenario deleted"}




@router.delete("/{scenario_id}")
async def delete_scenario(scenario_id: str, current_user=Depends(get_current_user)):
    user_email = current_user["email"]

    result = await db["scenarios"].delete_one({
        "scenario_id": scenario_id,
        "created_by": user_email
    })

    if result.deleted_count == 0:
        raise HTTPException(404, "Scenario not found or access denied")

    # FIX: decrement usage
    await decrement_usage(user_email, "scenarios_used")

    return {"ok": True, "message": "Scenario deleted"}


# -------------------------------------------------------------------
# 6. AI SCENARIO GENERATION (Story only)
# -------------------------------------------------------------------
@router.post(
    "/generate-from-story", response_model=ScenarioGenerationResponse,
    dependencies=[Depends(feature_required("story_management"))],
)
async def generate_scenarios_from_story(
    story_id: str = Query(...),
    count: int = Query(3, ge=1, le=20),
    complexity: str = Query("basic"),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("ai_generation")),
):
    try:
        user = current_user
        email = user["email"]
        user_id = user.get("_id") or email

        story = await db["stories"].find_one({"story_id": story_id, "created_by": email})
        if not story:
            raise HTTPException(404, "Story not found.")

        sub = await get_subscription(user_id)

        existing = await db["scenarios"].count_documents({"created_by": email})
        max_scen = sub["limits"]["scenarios_limit"]
        rem_scen = max_scen - existing

        ai_used = sub["usage"]["ai_gen_used"]
        ai_lim = sub["limits"]["ai_gen_limit"]
        rem_ai = ai_lim - ai_used

        allowed = min(count, rem_ai, rem_scen)
        if allowed <= 0:
            return ScenarioGenerationResponse(
                scenarios=[],
                summary=ScenarioGenerationSummary(
                    message="No AI scenario generations left.",
                    remaining_ai_generations=rem_ai,
                    remaining_scenario_slots=rem_scen,
                    plan=sub["plan"],
                ),
            )

        project = await db["projects"].find_one(
            {"project_id": story["project_id"]}
        )
        agent = project.get("agent_identities", {}).get(
            "scenario_builder", "Scenario Builder"
        )

        prompt = build_scenario_prompt_from_story(agent, story, allowed, complexity)
        ai_list = await generate_scenarios_from_prompt(prompt)
        ai_list = ai_list[:allowed]

        created = []

        for item in ai_list:
            scenario_id = await get_next_sequence("scenario_id", "SC")

            raw_steps = item.get("steps", [])
            normalized_steps = [
                normalize_step_dict(step, i)
                for i, step in enumerate(raw_steps, start=1)
            ]

            doc = {
                "scenario_id": scenario_id,
                "story_id": story_id,
                "project_id": story["project_id"],
                "title": item["title"],
                "description": item.get("description", ""),
                "steps": normalized_steps,
                "status": "pending",
                "complexity": complexity,
                "created_by": email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "approved": False,
                "generated_by_agent": agent,
            }

            res = await db["scenarios"].insert_one(doc)
            doc["_id"] = res.inserted_id

            created.append(_build_scenario_response(doc))

            await increment_usage(user_id, "ai_gen_used")
            await increment_usage(user_id, "scenarios_used")

        return ScenarioGenerationResponse(
            scenarios=created,
            summary=ScenarioGenerationSummary(
                message=f"{allowed} scenarios generated.",
                remaining_ai_generations=max(rem_ai - allowed, 0),
                remaining_scenario_slots=max(rem_scen - allowed, 0),
                plan=sub["plan"],
            ),
        )

    except Exception as e:
        raise HTTPException(500, str(e))


# -------------------------------------------------------------------
# 7. AI SCENARIO GENERATION (Recording + Story)
# -------------------------------------------------------------------
@router.post(
    "/generate-from-recording", response_model=ScenarioGenerationResponse,
    dependencies=[Depends(feature_required("story_management", "recorder"))],
)
async def generate_from_recording(
    story_id: str = Query(...),
    recording_id: str = Query(...),
    count: int = Query(3, ge=1, le=20),
    complexity: str = Query("medium"),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("ai_generation")),
):
    try:
        user = current_user
        email = user["email"]
        user_id = user.get("_id") or email

        story = await db["stories"].find_one({"story_id": story_id, "created_by": email})
        if not story:
            raise HTTPException(404, "Story not found.")

        recording = await db["recordings"].find_one(
            {"recording_id": recording_id, "created_by": email}
        )
        if not recording:
            raise HTTPException(404, "Recording not found.")

        sub = await get_subscription(user_id)

        total_existing = await db["scenarios"].count_documents({"created_by": email})
        max_scen = sub["limits"]["scenarios_limit"]
        rem_scen = max_scen - total_existing

        ai_used = sub["usage"]["ai_gen_used"]
        ai_lim = sub["limits"]["ai_gen_limit"]
        rem_ai = ai_lim - ai_used

        allowed = min(count, rem_ai, rem_scen)
        if allowed <= 0:
            return ScenarioGenerationResponse(
                scenarios=[],
                summary=ScenarioGenerationSummary(
                    message="No remaining AI generations.",
                    remaining_ai_generations=rem_ai,
                    remaining_scenario_slots=rem_scen,
                    plan=sub["plan"],
                ),
            )

        project = await db["projects"].find_one(
            {"project_id": story["project_id"]}
        )
        agent_name = project.get("agent_identities", {}).get(
            "scenario_builder", "Scenario Builder"
        )

        prompt = build_scenario_prompt_from_recording(
            agent_name, story, recording, allowed, complexity
        )
        ai_result = await generate_scenarios_from_prompt(prompt)

        created_docs = []
        ai_result = ai_result[:allowed]

        for item in ai_result:
            scenario_id = await get_next_sequence("scenario_id", "SC")

            raw_steps = item.get("steps", [])
            normalized_steps = [
                normalize_step_dict(step, i)
                for i, step in enumerate(raw_steps, start=1)
            ]

            doc = {
                "scenario_id": scenario_id,
                "story_id": story_id,
                "project_id": story["project_id"],
                "title": item["title"],
                "description": item.get("description", ""),
                "steps": normalized_steps,
                "status": "pending",
                "complexity": complexity,
                "created_by": email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "generated_by_agent": agent_name,
                "approved": False,
            }

            result = await db["scenarios"].insert_one(doc)
            doc["_id"] = result.inserted_id
            created_docs.append(_build_scenario_response(doc))

            await increment_usage(user_id, "ai_gen_used")
            await increment_usage(user_id, "scenarios_used")

        return ScenarioGenerationResponse(
            scenarios=created_docs,
            summary=ScenarioGenerationSummary(
                message=f"{allowed} scenarios generated from recording.",
                remaining_ai_generations=max(rem_ai - allowed, 0),
                remaining_scenario_slots=max(rem_scen - allowed, 0),
                plan=sub["plan"],
            ),
        )

    except Exception as e:
        raise HTTPException(500, str(e))


# ------------------------------------------------------
# 8. APPROVE SCENARIO
# ------------------------------------------------------
@router.put("/{scenario_id}/approve", response_model=ScenarioResponse)
async def approve_scenario(
    scenario_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    user_email = current_user["email"]

    scenario = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": user_email}
    )
    if not scenario:
        raise HTTPException(404, "Scenario not found.")

    await db["scenarios"].update_one(
        {"scenario_id": scenario_id},
        {"$set": {"approved": True}}
    )

    updated = await db["scenarios"].find_one({"scenario_id": scenario_id})
    return _build_scenario_response(updated)


# ------------------------------------------------------
# 9. UNAPPROVE SCENARIO
# ------------------------------------------------------
@router.put("/{scenario_id}/unapprove", response_model=ScenarioResponse)
async def unapprove_scenario(
    scenario_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    user_email = current_user["email"]

    scenario = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": user_email}
    )
    if not scenario:
        raise HTTPException(404, "Scenario not found.")

    await db["scenarios"].update_one(
        {"scenario_id": scenario_id},
        {"$set": {"approved": False}}
    )

    updated = await db["scenarios"].find_one({"scenario_id": scenario_id})
    return _build_scenario_response(updated)
