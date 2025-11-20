from fastapi import APIRouter, HTTPException, Depends, Query, status
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
from app.routes.recorder_routes import get_recording_for_story

from app.ai.scenario_prompts import (
    build_scenario_prompt_from_story,
    build_scenario_prompt_from_recording,
)

from app.services.ai.scenario_generator import generate_scenarios_from_prompt


# ------------------------------------------------------
# Router Setup
# ------------------------------------------------------
router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


# ------------------------------------------------------
# STEP NORMALIZATION
# ------------------------------------------------------
def normalize_step(raw, idx):
    """
    Normalize ANY raw step shape (string, dict, list) into a consistent StepModel-compatible dict.
    """

    if isinstance(raw, dict):
        return {
            "step_id": raw.get("step_id", f"STEP{idx:03d}"),
            "category": raw.get("category", "General"),
            "action": raw.get("action", "Undefined action"),
            "expected": raw.get("expected", "No expected result")
        }

    if isinstance(raw, str):
        return {
            "step_id": f"STEP{idx:03d}",
            "category": "General",
            "action": raw,
            "expected": "Expected result not provided"
        }

    if isinstance(raw, list):
        return {
            "step_id": f"STEP{idx:03d}",
            "category": "General",
            "action": " → ".join(str(x) for x in raw),
            "expected": "Expected result not provided"
        }

    return {
        "step_id": f"STEP{idx:03d}",
        "category": "General",
        "action": str(raw),
        "expected": "Expected result not provided"
    }


def _build_scenario_response(doc):
    steps = doc.get("steps", [])

    normalized_steps  = [
        normalize_step(step_raw , idx)
        for idx, step_raw in enumerate(steps, start=1)
    ]

    return ScenarioResponse(
        scenario_id=doc["scenario_id"],
        story_id=doc["story_id"],
        project_id=doc["project_id"],
        title=doc["title"],
        description=doc.get("description", ""),
        steps=normalized_steps ,
        status=doc.get("status", "pending"),
        complexity=doc.get("complexity", ""),
        created_by=doc.get("created_by", ""),
        created_at=doc.get("created_at", ""),
        generated_by_agent=str(doc.get("generated_by_agent")) if doc.get("generated_by_agent") else None,
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

        doc = {
            "scenario_id": scenario_id,
            "story_id": scenario.story_id,
            "project_id": story["project_id"],
            "title": scenario.title,
            "description": scenario.description,
            "steps": scenario.steps or [],
            "status": "pending",
            "complexity": scenario.complexity,
            "generated_by_agent": agent_name,
            "created_by": user_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
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
# 4. UPDATE SCENARIO
# -------------------------------------------------------------------
@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    update: ScenarioUpdate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    email = current_user["email"]
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    result = await db["scenarios"].update_one(
        {"scenario_id": scenario_id, "created_by": email},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Scenario not found or access denied.")

    updated = await db["scenarios"].find_one({"scenario_id": scenario_id, "created_by": email})
    return _build_scenario_response(updated)


# -------------------------------------------------------------------
# 5. DELETE SCENARIO
# -------------------------------------------------------------------
@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    email = current_user["email"]
    res = await db["scenarios"].delete_one({"scenario_id": scenario_id, "created_by": email})
    if res.deleted_count == 0:
        raise HTTPException(404, "Scenario not found.")
    return {"message": "Scenario deleted"}


# -------------------------------------------------------------------
# 6. AI SCENARIO GENERATION (Story + Recording Integration)
# -------------------------------------------------------------------
@router.post("/generate-from-story", response_model=ScenarioGenerationResponse)
async def generate_scenarios_from_story(
    story_id: str = Query(...),
    count: int = Query(3, ge=1, le=20),
    complexity: str = Query(
        'basic',
        description='Scenario complexity: basic | medium | advanced',
    ),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("ai_generation")),
):
    """
    Next-generation scenario generator:
    - Uses Option A+ subscription model (safe, never errors)
    - Accepts both:
        a) Story-only generation
        b) Recording-only generation
        c) Story + Recording combined prompt
    """
    try:
        user_id = current_user.get("_id") or current_user.get("email")
        email = current_user["email"]

        # ------------------------------------------------------
        # 1️⃣ Load story
        # ------------------------------------------------------
        story = await db["stories"].find_one({"story_id": story_id, "created_by": email})
        if not story:
            raise HTTPException(404, "Story not found.")

        # ------------------------------------------------------
        # 2️⃣ Subscription limits
        # ------------------------------------------------------
        sub = await get_subscription(user_id)

        existing = await db["scenarios"].count_documents({"created_by": email})

        max_scenarios = sub["limits"]["scenarios_limit"]
        used_ai = sub["usage"]["ai_gen_used"]
        ai_limit = sub["limits"]["ai_gen_limit"]

        remaining_scenarios = max_scenarios - existing
        remaining_ai = ai_limit - used_ai

        allowed = min(count, remaining_ai, remaining_scenarios)

        if allowed <= 0:
            return ScenarioGenerationResponse(
                scenarios=[],
                summary=ScenarioGenerationSummary(
                    message="No AI scenario generations left in your plan.",
                    remaining_ai_generations=remaining_ai,
                    remaining_scenario_slots=remaining_scenarios,
                    plan=sub["plan"],
                )
            )

        # ------------------------------------------------------
        # 3️⃣ Fetch Agent name
        # ------------------------------------------------------
        project = await db["projects"].find_one({"project_id": story["project_id"]})
        agent_name = project.get("agent_identities", {}).get("scenario_builder", "Scenario Builder")

        # ------------------------------------------------------
        # 5️⃣ Build the correct AI prompt
        # ------------------------------------------------------
        prompt = build_scenario_prompt_from_story(agent_name, story, allowed, complexity)

        # ------------------------------------------------------
        # 6️⃣ Run AI
        # ------------------------------------------------------
        ai_list = await generate_scenarios_from_prompt(prompt)
        
        if not isinstance(ai_list, list):
            raise HTTPException(500, 'AI generator returned invalid data.')
        ai_list = ai_list[:allowed]
        created_docs = []

        # ------------------------------------------------------
        # 7️⃣ Store scenarios
        # ------------------------------------------------------
        for item in ai_list:
            scenario_id = await get_next_sequence("scenario_id", "SC")

            steps = [
                {
                    "step_id": f"STEP{i:03d}",
                    "category": s.get("category", "General"),
                    "action": s.get("action", ""),
                    "expected": s.get("expected", ""),
                }
                for i, s in enumerate(item.get("steps", []), start=1)
            ]

            doc = {
                "scenario_id": scenario_id,
                "story_id": story_id,
                "project_id": story["project_id"],
                "title": item["title"],
                "description": item.get("description", ""),
                "steps": steps,
                "status": "pending",
                "complexity": complexity,
                "created_by": email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "generated_by_agent": agent_name,
            }

            res = await db["scenarios"].insert_one(doc)
            doc["_id"] = res.inserted_id

            created_docs.append(_build_scenario_response(doc))

            await increment_usage(user_id, "ai_gen_used")
            await increment_usage(user_id, "scenarios_used")

        # ------------------------------------------------------
        # 8️⃣ Build summary response
        # ------------------------------------------------------
        return ScenarioGenerationResponse(
            scenarios=created_docs,
            summary=ScenarioGenerationSummary(
                message=f"{allowed} scenarios generated by agent '{agent_name}'.",
                remaining_ai_generations=max(remaining_ai - allowed, 0),
                remaining_scenario_slots=max(remaining_scenarios - allowed, 0),
                plan=sub["plan"]
            )
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))


# -------------------------------------------------------------------
# 7. AI SCENARIO GENERATION from Recording (with complexity)
# -------------------------------------------------------------------
@router.post(
    '/generate-from-recording',
    response_model=ScenarioGenerationResponse,
)
async def generate_scenarios_from_recording_endpoint(
    story_id: str = Query(..., description='Business story_id, e.g. S001'),
    recording_id: str = Query(..., description='Recording ID, e.g. REC001'),
    count: int = Query(3, ge=1, le=20),
    complexity: str = Query(
        'medium',
        description='Scenario complexity: basic | medium | advanced',
    ),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required('ai_generation')),
):
    """
    Generate scenarios using STORY + RECORDING as input.

    Uses the same subscription soft-limit logic as generate-from-story.
    """

    try:
        user_id = (
            current_user.get('_id')
            or current_user.get('id')
            or current_user.get('email')
        )
        user_email = current_user.get('email')

        # 1️⃣ LOAD STORY
        story = await db['stories'].find_one(
            {'story_id': story_id, 'created_by': user_email}
        )
        if not story:
            raise HTTPException(404, 'Story not found or access denied.')

        # 2️⃣ LOAD RECORDING (single doc)
        recording = await db['recordings'].find_one(
            {'recording_id': recording_id, 'created_by': user_email}
        )
        if not recording:
            raise HTTPException(
                404, 'Recording not found or access denied for this user.'
            )

        # 3️⃣ SUBSCRIPTION LIMITS
        sub = await get_subscription(user_id)

        total_existing = await db['scenarios'].count_documents(
            {'created_by': user_email}
        )
        max_scenarios = sub['limits'].get('scenarios_limit', None)
        remaining_scenarios = (
            max_scenarios - total_existing if max_scenarios is not None else None
        )

        used_ai = sub['usage'].get('ai_gen_used', 0)
        ai_limit = sub['limits'].get('ai_gen_limit', None)
        remaining_ai = (
            ai_limit - used_ai if ai_limit is not None else None
        )

        allowed_count = count

        if remaining_ai is not None:
            allowed_count = min(allowed_count, remaining_ai)

        if remaining_scenarios is not None:
            allowed_count = min(allowed_count, remaining_scenarios)

        if allowed_count <= 0:
            return ScenarioGenerationResponse(
                scenarios=[],
                summary=ScenarioGenerationSummary(
                    message='No AI generations left for your plan.',
                    remaining_ai_generations=remaining_ai,
                    remaining_scenario_slots=remaining_scenarios,
                    plan=sub['plan'],
                ),
            )

        # 4️⃣ FETCH PROJECT → AGENT IDENTITY
        project = await db['projects'].find_one(
            {'project_id': story['project_id']}
        )
        if not project:
            raise HTTPException(
                404, 'Project not found. Please create a project first.'
            )

        agent_name = project.get('agent_identities', {}).get(
            'scenario_builder', 'Scenario Builder'
        )

        # 5️⃣ BUILD PROMPT (story + recording)
        prompt = build_scenario_prompt_from_recording(
            agent_name=agent_name,
            story=story,
            recording=recording,
            count=allowed_count,
            complexity=complexity,
        )

        # 6️⃣ CALL AI
        ai_result = await generate_scenarios_from_prompt(prompt)

        if not isinstance(ai_result, list):
            raise HTTPException(500, 'AI generator returned invalid data.')

        created_docs: List[ScenarioResponse] = []
        ai_result = ai_result[:allowed_count]

        # 7️⃣ SAVE SCENARIOS
        for scenario in ai_result:
            scenario_id = await get_next_sequence('scenario_id', 'SC')

            raw_steps = scenario.get('steps', [])
            normalized_steps = []
            for idx, step in enumerate(raw_steps, start=1):
                normalized_steps.append(
                    {
                        'step_id': f'STEP{idx:03d}',
                        'category': step.get('category', 'General'),
                        'action': step.get('action', ''),
                        'expected': step.get('expected', ''),
                    }
                )

            doc = {
                'scenario_id': scenario_id,
                'story_id': story_id,
                'project_id': story['project_id'],
                'title': scenario['title'],
                'description': scenario.get('description', ''),
                'steps': normalized_steps,
                'status': 'pending',
                "complexity": complexity,
                'created_by': user_email,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'generated_by_agent': agent_name,
            }

            result = await db['scenarios'].insert_one(doc)
            doc['_id'] = result.inserted_id
            created_docs.append(_build_scenario_response(doc))

            await increment_usage(user_id, 'ai_gen_used')
            await increment_usage(user_id, 'scenarios_used')

        # 8️⃣ SUMMARY
        new_remaining_ai = (
            remaining_ai - allowed_count
            if remaining_ai is not None
            else 'unlimited'
        )
        new_remaining_slots = (
            remaining_scenarios - allowed_count
            if remaining_scenarios is not None
            else 'unlimited'
        )

        return ScenarioGenerationResponse(
            scenarios=created_docs,
            summary=ScenarioGenerationSummary(
                message=(
                    f'{allowed_count} scenarios generated successfully '
                    f"from recording '{recording_id}' by agent '{agent_name}'."
                ),
                remaining_ai_generations=new_remaining_ai,
                remaining_scenario_slots=new_remaining_slots,
                plan=sub['plan'],
            ),
        )

    except Exception as e:
        import traceback

        print('\n\n🔥 DEBUG ERROR (generate-from-recording) 🔥')
        traceback.print_exc()
        raise HTTPException(500, str(e))