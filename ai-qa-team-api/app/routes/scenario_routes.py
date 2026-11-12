from app.services.prompt_registry_service import get_active as get_active_prompt
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
from app.services.ai.ai_configuration_service import public_error
from app.services.ai.base_provider import LLMProviderError
from app.services.ai.ai_usage_policy import AIUsageError
from app.services.knowledge_test_design import KnowledgeTestDesign
from app.models.test_design import ScenarioIntent
from pydantic import ValidationError
from app.services.subscription_services import decrement_usage
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_member
from app.config import settings

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
        **{key: doc[key] for key in ("spec_kind", "purpose", "role", "coverage_type", "expected_outcome", "preconditions",
                                   "acceptance_criteria_refs", "rule_references", "knowledge_version_id", "story_analysis_id") if key in doc},
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
@router.post("", response_model=ScenarioResponse, include_in_schema=False)
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
            normalize_step_dict(step.model_dump(), idx)
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

        await require_project_member(story["project_id"], current_user)
        if settings.features.product_knowledge:
            context = await KnowledgeTestDesign(db).knowledge.generation_context(story["project_id"], story["story_id"])
            try:
                intent = ScenarioIntent(title=scenario.title, description=scenario.description or "",
                    purpose=scenario.purpose or scenario.description or scenario.title, role=scenario.role,
                    coverage_type=scenario.coverage_type or "happy_path", preconditions=scenario.preconditions,
                    expected_outcome=scenario.expected_outcome or "",
                    acceptance_criteria_refs=scenario.acceptance_criteria_refs or [story["acceptance_criteria"]],
                    rule_references=scenario.rule_references)
            except ValidationError:
                raise HTTPException(422, "Complete the scenario intent and explicit expected outcome.") from None
            KnowledgeTestDesign.references(intent, story, context["knowledge"])
            doc.update({**intent.model_dump(), "steps": [], "spec_kind": "coverage-intent-v1",
                        "knowledge_version_id": context["knowledge"]["version_id"],
                        "story_analysis_id": context["analysis"]["analysis_id"]})

        result = await db["scenarios"].insert_one(doc)
        doc["_id"] = result.inserted_id
        return _build_scenario_response(doc)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Scenario could not be created.") from None


# -------------------------------------------------------------------
# 2. LIST SCENARIOS for a story
# -------------------------------------------------------------------
@router.get("", response_model=List[ScenarioResponse], include_in_schema=False)
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
# 3. PROJECT OVERVIEW AND SINGLE SCENARIO
# -------------------------------------------------------------------
@router.get("/project-list", response_model=List[ScenarioResponse],
            dependencies=[Depends(feature_required("scenario_generation"))])
async def project_scenarios(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    await require_project_member(project_id, current_user)
    cursor = db["scenarios"].find({"project_id": project_id}).sort("scenario_id", 1).skip(skip).limit(limit)
    return [_build_scenario_response(doc) async for doc in cursor]


@router.get("/project-overview")
async def project_scenario_overview(
    project_id: str,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    await require_project_member(project_id, current_user)
    # Match the Stories screen's owner scope and bound the overview payload.
    story_ids = await db["stories"].distinct(
        "story_id", {"project_id": project_id, "created_by": current_user["email"]}
    )
    if not story_ids:
        return {"total": 0, "recent": []}
    summaries = await db["scenarios"].aggregate([
        {"$match": {"project_id": project_id, "story_id": {"$in": story_ids}}},
        {"$facet": {
            "count": [{"$count": "total"}],
            "recent": [
                {"$sort": {"created_at": -1, "_id": -1}},
                {"$limit": 5},
                {"$project": {"_id": 0, "scenario_id": 1, "story_id": 1, "title": 1,
                              "approved": 1, "complexity": 1}},
            ],
        }},
    ]).to_list(1)
    summary = summaries[0] if summaries else {"count": [], "recent": []}
    return {"total": summary["count"][0]["total"] if summary["count"] else 0, "recent": summary["recent"]}


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

    await require_project_member(existing["project_id"], current_user)

    update_data = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
    if existing.get("spec_kind") == "coverage-intent-v1" and update_data.get("approved"):
        raise HTTPException(409, "Use the approval operation to validate current knowledge and story context.")

    # Preserve existing approval flag if not explicitly updated
    if "approved" not in update_data:
        update_data["approved"] = existing.get("approved", False)

    if any(field in update_data for field in ("title", "description", "steps", "purpose", "role", "coverage_type", "expected_outcome", "preconditions", "acceptance_criteria_refs", "rule_references")):
        update_data["approved"] = False

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

    existing = await db["scenarios"].find_one({"scenario_id": scenario_id, "created_by": user_email})
    if not existing:
        raise HTTPException(404, "Scenario not found or access denied")
    await require_project_member(existing["project_id"], current_user)
    scope = {"project_id": existing["project_id"], "scenario_id": scenario_id}
    for collection in ("testcases", "approved_visual_tests", "visual_test_spec_versions", "executions"):
        if await db[collection].find_one(scope):
            raise HTTPException(409, "This scenario has dependent tests, approvals or history and cannot be deleted.")

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

        await require_project_member(story["project_id"], current_user)
        existing = await db["scenarios"].count_documents({"created_by": email})
        max_scen = sub["limits"]["scenarios_limit"]
        rem_scen = None if max_scen is None else max(max_scen - existing, 0)
        ai_used = sub["usage"]["ai_gen_used"]
        ai_lim = sub["limits"]["ai_gen_limit"]
        rem_ai = None if ai_lim is None else max(ai_lim - ai_used, 0)
        knowledge_mode = settings.features.product_knowledge
        allowed = count if rem_scen is None else min(count, rem_scen)
        if not knowledge_mode and rem_ai is not None:
            allowed = min(allowed, rem_ai)
        if allowed <= 0 or rem_ai == 0:
            return ScenarioGenerationResponse(scenarios=[], summary=ScenarioGenerationSummary(
                message="Scenario or AI allowance is exhausted.", requested_count=count, allowed_count=0, generated_count=0,
                remaining_ai_generations=rem_ai, remaining_scenario_slots=rem_scen, plan=sub["plan"]))

        project = await db["projects"].find_one(
            {"project_id": story["project_id"]}
        )
        agent = project.get("agent_identities", {}).get(
            "scenario_builder", "Scenario Builder"
        )

        context = None
        if knowledge_mode:
            ai_list, context = await KnowledgeTestDesign(db).scenarios(story["project_id"], current_user, story, allowed, complexity)
        else:
            resolved_prompt = await get_active_prompt("LEGACY_STORY_SCENARIOS", database=db)
            prompt = build_scenario_prompt_from_story(agent, story, allowed, complexity, template=resolved_prompt["system_prompt"])
            ai_list = (await generate_scenarios_from_prompt(story["project_id"], prompt,
                prompt_key=resolved_prompt["prompt_key"], prompt_version=str(resolved_prompt["resolved_version"])))[:allowed]

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
                **({"prompt_key": resolved_prompt["prompt_key"], "prompt_version": str(resolved_prompt["resolved_version"])} if not knowledge_mode else {}),
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

            if context:
                doc.update({**item, "spec_kind": "coverage-intent-v1", "steps": [],
                            "knowledge_version_id": context["knowledge"]["version_id"],
                            "story_analysis_id": context["analysis"]["analysis_id"]})

            res = await db["scenarios"].insert_one(doc)
            doc["_id"] = res.inserted_id

            created.append(_build_scenario_response(doc))

            if not knowledge_mode:
                await increment_usage(user_id, "ai_gen_used")
            await increment_usage(user_id, "scenarios_used")

        actual = len(created)
        spent = 1 if knowledge_mode else actual
        return ScenarioGenerationResponse(scenarios=created, summary=ScenarioGenerationSummary(
            message=f"{actual} of {count} requested scenarios generated (allowed {allowed}).",
            requested_count=count, allowed_count=allowed, generated_count=actual,
            remaining_ai_generations=None if rem_ai is None else max(rem_ai - spent, 0),
            remaining_scenario_slots=None if rem_scen is None else max(rem_scen - actual, 0), plan=sub["plan"]))

    except AIUsageError as exc:
        raise HTTPException(exc.status_code, exc.public_detail()) from None
    except LLMProviderError as exc:
        raise public_error(exc) from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, "Scenario generation could not be completed.") from None


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

        resolved_prompt = await get_active_prompt("LEGACY_RECORDING_SCENARIOS", database=db)
        prompt = build_scenario_prompt_from_recording(
            agent_name, story, recording, allowed, complexity, template=resolved_prompt["system_prompt"]
        )
        ai_result = await generate_scenarios_from_prompt(story["project_id"], prompt,
            prompt_key=resolved_prompt["prompt_key"], prompt_version=str(resolved_prompt["resolved_version"]))

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
                "prompt_key": resolved_prompt["prompt_key"], "prompt_version": str(resolved_prompt["resolved_version"]),
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

    await require_project_member(scenario["project_id"], current_user)
    if scenario.get("spec_kind") == "coverage-intent-v1":
        context = await KnowledgeTestDesign(db).knowledge.generation_context(scenario["project_id"], scenario["story_id"])
        if (scenario.get("knowledge_version_id") != context["knowledge"]["version_id"]
                or scenario.get("story_analysis_id") != context["analysis"]["analysis_id"]):
            raise HTTPException(409, "Knowledge or story analysis changed. Create a successor scenario.")
        try:
            intent = ScenarioIntent(**{key: scenario.get(key) for key in ScenarioIntent.model_fields})
        except ValidationError:
            raise HTTPException(422, "Complete the scenario intent and expected outcome before approval.") from None
        story = await KnowledgeTestDesign(db).knowledge.story(scenario["project_id"], scenario["story_id"])
        KnowledgeTestDesign.references(intent, story, context["knowledge"])
    await db["scenarios"].update_one(
        {"scenario_id": scenario_id, "project_id": scenario["project_id"]},
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
