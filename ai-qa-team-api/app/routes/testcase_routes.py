from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from uuid import uuid4

from app.db.connection import db
from app.routes.auth_routes import get_current_user
from app.services.story_service import get_next_sequence
from app.models.test_case_model import TestCaseResponse, TestStep, TestCaseCreate
from app.utils.subscription_dependency import subscription_required
from app.services.subscription_services import get_subscription, increment_usage
from app.services.test_generator import generate_playwright_test
from app.config import settings
from app.services.step_mapper import StepMapper
from app.services.knowledge_test_design import KnowledgeTestDesign
from app.services.ai.ai_usage_policy import AIUsageError
from app.services.ai.base_provider import LLMProviderError
from app.services.ai.ai_configuration_service import public_error

from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_member

router = APIRouter(prefix="/testcases", tags=["Test Cases"])


def normalize_steps(raw_steps: list) -> list[TestStep]:
    """
    Accepts natural language, recorder format, or partial structured.
    Always returns a clean List[TestStep].

    Used when user manually edits test case via PUT.
    """
    normalized: list[TestStep] = []

    for s in raw_steps:
        # Already TestStep instance
        if isinstance(s, TestStep):
            normalized.append(s)
            continue

        # Plain dict → TestStep (best-effort)
        if isinstance(s, dict):
            normalized.append(TestStep(**s))
            continue

    return normalized


# ==========================================================
# 1) Generate testcases from an APPROVED scenario
# ==========================================================
@router.post(
    "/generate", response_model=List[TestCaseResponse],
    dependencies=[Depends(feature_required("test_generation"))],
    include_in_schema=settings.features.test_generation,
)
async def generate_testcases(
    scenario_id: str = Query(...),
    count: int = Query(1, ge=1, le=20),
    complexity: str = Query("basic", regex="^(basic|medium|advanced)$"),
    project_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    """
    Generate one or more test cases from a *single approved scenario*.

    - Enforces scenario.approved == True
    - Enforces plan-based complexity rules
    - Enforces testcases_limit from subscription
    - Uses StepMapper to produce structured steps
    """
    user_email = current_user["email"]
    user_id = current_user.get("_id") or user_email

    # -------------------------------------
    # 1) Load Scenario & enforce approval
    # -------------------------------------
    scenario_query = {"scenario_id": scenario_id, "created_by": user_email}
    if project_id is not None:
        scenario_query["project_id"] = project_id
    scenario = await db["scenarios"].find_one(scenario_query)
    if not scenario:
        raise HTTPException(404, "Scenario not found.")
    await require_project_member(scenario["project_id"], current_user)

    if not scenario.get("approved", False):
        raise HTTPException(
            400,
            "Scenario must be approved before generating test cases.",
        )

    # -------------------------------------
    # 2) Subscription & complexity gating
    # -------------------------------------
    sub = await get_subscription(user_id)
    if not sub:
        raise HTTPException(403, "No active subscription found.")

    plan = sub["plan"]

    # Plan-based complexity rules
    if plan == "free" and complexity != "basic":
        raise HTTPException(
            403,
            "Free plan supports only 'basic' test cases. Upgrade to Pro for medium/advanced.",
        )

    # Testcase quotas
    limits = sub["limits"]
    tier_limits = {tier: limits.get(f"testcases_{tier}_limit") for tier in ("basic", "medium", "advanced")}
    total_limit = limits.get("testcases_limit")
    if total_limit in (None, 0) and any(value is not None for value in tier_limits.values()):
        # Older subscriptions defaulted the unused aggregate to zero.
        total_limit = sum(value or 0 for value in tier_limits.values())
    testcase_owner = {"created_by": user_email}
    used_total = await db["testcases"].count_documents(testcase_owner)
    if sub.get("billing_scope") == "ACCOUNT":
        used_total = sub["usage"].get("testcases_used", 0)
    allowed = count if total_limit is None else min(count, max(total_limit - used_total, 0))
    tier_limit = tier_limits[complexity]
    if tier_limit is not None:
        legacy_levels = [complexity, None] if complexity == "basic" else [complexity]
        used_tier = await db["testcases"].count_documents({
            **testcase_owner,
            "$or": [
                {"complexity": complexity},
                {"complexity": None, "level": {"$in": legacy_levels}},
            ],
        })
        if sub.get("billing_scope") == "ACCOUNT":
            used_tier = sub["usage"].get(f"testcases_{complexity}_used", 0)
        allowed = min(allowed, max(tier_limit - used_tier, 0))

    if allowed <= 0:
        raise HTTPException(
            403,
            f"Test case generation limit reached for {complexity} cases.",
        )

    knowledge_plans = None
    if settings.features.product_knowledge and scenario.get("spec_kind") != "coverage-intent-v1":
        raise HTTPException(409, "Preserve this legacy scenario. Create and approve a coverage intent against current knowledge before generating new detailed cases.")
    if scenario.get("spec_kind") == "coverage-intent-v1":
        try:
            knowledge_plans, _ = await KnowledgeTestDesign(db).testcases(scenario["project_id"], current_user, scenario, allowed)
        except AIUsageError as exc:
            raise HTTPException(exc.status_code, exc.public_detail()) from None
        except LLMProviderError as exc:
            raise public_error(exc) from None
        allowed = len(knowledge_plans)

    # -------------------------------------
    # 3) StepMapper: scenario steps → structured
    # -------------------------------------
    mapper = StepMapper()
    nl_steps = scenario.get("steps", [])

    generated_cases: List[TestCaseResponse] = []

    for index in range(allowed):
        testcase_id = await get_next_sequence("testcase_id", "TC")

        structured_steps_dicts = [
            mapper.to_structured(step) for step in nl_steps
        ]
        structured_steps = [TestStep(**s) for s in structured_steps_dicts]

        # Generate Playwright code from structured steps
        code = generate_playwright_test(scenario)

        doc = {
            "testcase_id": testcase_id,
            "scenario_id": scenario_id,
            "project_id": scenario["project_id"],
            "title": scenario["title"],
            "description": scenario.get("description", ""),

            # dual representation
            "natural_steps": nl_steps,
            "steps": [s.model_dump() for s in structured_steps],

            "complexity": complexity,
            "status": "generated",
            "code": code,
            "created_by": user_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": None,
            "updated_at": None,
            # optional test-data linking
            "data_set_id": None,
            "data_overrides": {},
        }

        if knowledge_plans is not None:
            plan = knowledge_plans[index]
            doc.update({**plan, "title": plan["title"], "description": plan["purpose"], "code": "",
                        "status": "draft", "spec_kind": "detailed-case-v1",
                        "knowledge_version_id": scenario["knowledge_version_id"],
                        "story_analysis_id": scenario["story_analysis_id"],
                        "natural_steps": [{"action": step["instruction"], "expected": step["expected"]} for step in plan["procedure"]],
                        "steps": [{"action": "unknown", "description": step["instruction"], "expected": step["expected"]} for step in plan["procedure"]]})

        res = await db["testcases"].insert_one(doc)
        doc["_id"] = str(res.inserted_id)
        doc.pop("_id", None)

        generated_cases.append(
            TestCaseResponse(
                testcase_id=doc["testcase_id"],
                scenario_id=doc["scenario_id"],
                project_id=doc["project_id"],
                title=doc["title"],
                description=doc.get("description"),
                **{key: doc[key] for key in ("spec_kind", "purpose", "role", "preconditions", "public_data", "assertions", "cleanup",
                                           "acceptance_criteria_refs", "rule_references", "knowledge_version_id", "story_analysis_id") if key in doc},
                complexity=doc.get("complexity"),
                steps=[TestStep(**s) for s in doc.get("steps", [])],
                status=doc["status"],
                code=doc["code"],
                created_by=doc.get("created_by"),
                created_at=doc.get("created_at"),
                updated_by=doc.get("updated_by"),
                updated_at=doc.get("updated_at"),
            )
        )

        # Increment testcase usage
        await increment_usage(user_id, "testcases_used")
        if sub.get("billing_scope") == "ACCOUNT":
            await increment_usage(user_id, f"testcases_{complexity}_used")

    return generated_cases


# ==========================================================
# 2) UPDATE A TESTCASE (manual editing)
# ==========================================================
@router.put("/{testcase_id}", response_model=TestCaseResponse)
async def update_testcase(
    testcase_id: str,
    payload: TestCaseCreate,
    current_user=Depends(get_current_user),
):
    user_email = current_user["email"]

    existing = await db["testcases"].find_one(
        {"testcase_id": testcase_id, "created_by": user_email}
    )
    if not existing:
        raise HTTPException(404, "Testcase not found")

    await require_project_member(existing["project_id"], current_user)
    if payload.project_id and payload.project_id != existing["project_id"]:
        raise HTTPException(422, "Moving a test case between projects requires an explicit migration.")
    if payload.scenario_id and not await db["scenarios"].find_one({"project_id": existing["project_id"], "scenario_id": payload.scenario_id}):
        raise HTTPException(404, "Source scenario not found in this project.")

    # Normalize structured steps
    normalized_steps = normalize_steps(payload.steps or [])

    update_doc = {
        "title": payload.title,
        "description": payload.description,
        "scenario_id": payload.scenario_id or existing.get("scenario_id"),
        "project_id": payload.project_id or existing.get("project_id"),
        "steps": [s.model_dump() for s in normalized_steps],
        "natural_steps": payload.natural_steps or existing.get("natural_steps", []),
        "data_set_id": payload.data_set_id,
        "data_overrides": payload.data_overrides,
        "updated_by": user_email,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await db["testcases"].update_one(
        {"testcase_id": testcase_id, "created_by": user_email},
        {"$set": update_doc},
    )

    updated = await db["testcases"].find_one(
        {"testcase_id": testcase_id, "created_by": user_email}
    )
    if not updated:
        raise HTTPException(404, "Testcase not found after update")

    updated.pop("_id", None)
    updated["steps"] = [TestStep(**s) for s in updated.get("steps", [])]

    return TestCaseResponse(**updated)


# ==========================================================
# 3) GET SINGLE TESTCASE
# ==========================================================
@router.get("/testcases/{testcase_id}", response_model=TestCaseResponse)
async def get_testcase(
    testcase_id: str,
    current_user=Depends(get_current_user),
):
    doc = await db["testcases"].find_one({"testcase_id": testcase_id})
    if not doc:
        raise HTTPException(404, "Testcase not found")

    await require_project_member(doc["project_id"], current_user)

    doc.pop("_id", None)
    doc["steps"] = [TestStep(**s) for s in doc.get("steps", [])]

    return TestCaseResponse(**doc)


# ==========================================================
# 4) LIST TESTCASES (by scenario / project)
# ==========================================================
@router.get("/testcases", response_model=List[TestCaseResponse])
async def list_testcases(
    scenario_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios")),
):
    filter_q: dict = {}

    if project_id:
        await require_project_member(project_id, current_user)
    if scenario_id:
        scenario = await db["scenarios"].find_one({"scenario_id": scenario_id, **({"project_id": project_id} if project_id else {})})
        if not scenario:
            raise HTTPException(404, "Scenario not found in the selected project.")
        await require_project_member(scenario["project_id"], current_user)
        filter_q["project_id"] = scenario["project_id"]
    if not project_id and not scenario_id:
        filter_q["created_by"] = current_user["email"]

    if scenario_id:
        filter_q["scenario_id"] = scenario_id

    if project_id:
        filter_q["project_id"] = project_id

    cursor = db["testcases"].find(filter_q)

    results: List[TestCaseResponse] = []
    async for doc in cursor:
        if not project_id and not scenario_id:
            try:
                await require_project_member(doc["project_id"], current_user)
            except HTTPException as exc:
                if exc.status_code in (403, 404): continue
                raise
        doc.pop("_id", None)
        doc["steps"] = [TestStep(**s) for s in doc.get("steps", [])]
        results.append(TestCaseResponse(**doc))

    return results


@router.get("/project-list", response_model=List[TestCaseResponse],
            dependencies=[Depends(feature_required("test_generation"))])
async def project_testcases(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    await require_project_member(project_id, current_user)
    cursor = db["testcases"].find({"project_id": project_id}, {"_id": 0}).sort("testcase_id", 1).skip(skip).limit(limit)
    return [TestCaseResponse(**doc) async for doc in cursor]


class CatalogTestCaseEdit(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    steps: list[TestStep]


@router.patch("/{testcase_id}", response_model=TestCaseResponse,
              dependencies=[Depends(feature_required("test_generation"))])
async def edit_catalog_testcase(testcase_id: str, payload: CatalogTestCaseEdit,
                                project_id: str, current_user=Depends(get_current_user)):
    await require_project_member(project_id, current_user)
    scope = {"project_id": project_id, "testcase_id": testcase_id, "created_by": current_user["email"]}
    existing = await db["testcases"].find_one(scope)
    if not existing:
        raise HTTPException(404, "Test case not found or access denied")
    if not payload.title.strip():
        raise HTTPException(422, "Title is required")
    changes = {
        "title": payload.title.strip(), "description": payload.description,
        "steps": [step.model_dump() for step in payload.steps],
        "natural_steps": [{**((existing.get("natural_steps") or [])[index]
                                if index < len(existing.get("natural_steps") or []) else {}),
                           "action": step.description or step.action, "expected": step.expected}
                          for index, step in enumerate(payload.steps)],
        "updated_by": current_user["email"], "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db["testcases"].update_one(scope, {"$set": changes})
    return TestCaseResponse(**{**existing, **changes})


@router.delete("/{testcase_id}", dependencies=[Depends(feature_required("test_generation"))])
async def delete_catalog_testcase(testcase_id: str, project_id: str, current_user=Depends(get_current_user)):
    await require_project_member(project_id, current_user)
    scope = {"project_id": project_id, "testcase_id": testcase_id, "created_by": current_user["email"]}
    existing_case = await db["testcases"].find_one(scope)
    if not existing_case:
        raise HTTPException(404, "Test case not found or access denied")
    for collection in ("approved_visual_tests", "approved_visual_runs", "visual_test_spec_versions", "test_design_documents", "executions"):
        if await db[collection].find_one({"project_id": project_id, "testcase_id": testcase_id}):
            raise HTTPException(409, "This test case has approvals or execution history and cannot be deleted.")
    result = await db["testcases"].delete_one(scope)
    if result.deleted_count:
        from app.services.subscription_services import decrement_usage
        await decrement_usage(current_user["email"], "testcases_used")
        sub = await get_subscription(current_user["email"])
        if sub and sub.get("billing_scope") == "ACCOUNT":
            tier = existing_case.get("complexity") or existing_case.get("level") or "basic"
            if tier in ("basic", "medium", "advanced"):
                await decrement_usage(current_user["email"], f"testcases_{tier}_used")
    return {"ok": True}


@router.post("/draft", response_model=TestCaseResponse,
             dependencies=[Depends(feature_required("test_generation"))])
async def create_catalog_testcase(payload: CatalogTestCaseEdit, project_id: str,
                                  scenario_id: str, current_user=Depends(get_current_user)):
    await require_project_member(project_id, current_user)
    scenario = await db["scenarios"].find_one({"project_id": project_id, "scenario_id": scenario_id,
                                              "created_by": current_user["email"]})
    if not scenario:
        raise HTTPException(404, "Scenario not found or access denied")
    if not payload.title.strip():
        raise HTTPException(422, "Title is required")
    subscription = await get_subscription(current_user.get("_id") or current_user["email"])
    if not subscription:
        raise HTTPException(403, "No active subscription")
    limits = subscription["limits"]
    tier_limits = [limits.get(f"testcases_{tier}_limit") for tier in ("basic", "medium", "advanced")]
    total_limit = limits.get("testcases_limit")
    if total_limit in (None, 0) and any(value is not None for value in tier_limits):
        total_limit = sum(value or 0 for value in tier_limits)
    owner = {"created_by": current_user["email"]}
    total = await db["testcases"].count_documents(owner)
    basic = await db["testcases"].count_documents({**owner, "complexity": {"$in": ["basic", None]}})
    if subscription.get("billing_scope") == "ACCOUNT":
        total = subscription["usage"].get("testcases_used", 0)
        basic = subscription["usage"].get("testcases_basic_used", 0)
    if (total_limit is not None and total >= total_limit) or (tier_limits[0] is not None and basic >= tier_limits[0]):
        raise HTTPException(403, "Test case limit reached")
    doc = {"project_id": project_id, "scenario_id": scenario_id,
           "testcase_id": await get_next_sequence("testcase_id", "TC"),
           "title": payload.title.strip(), "description": payload.description,
           "steps": [step.model_dump() for step in payload.steps],
           "natural_steps": [{"action": step.description or step.action, "expected": step.expected} for step in payload.steps],
           "complexity": "basic", "status": "draft", "code": "", "created_by": current_user["email"],
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db["testcases"].insert_one(doc.copy())
    await increment_usage(current_user.get("_id") or current_user["email"], "testcases_used")
    if subscription.get("billing_scope") == "ACCOUNT":
        await increment_usage(current_user.get("_id") or current_user["email"], "testcases_basic_used")
    return TestCaseResponse(**doc)
