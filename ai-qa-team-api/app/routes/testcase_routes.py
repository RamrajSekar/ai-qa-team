from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
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

from openai import AsyncOpenAI

router = APIRouter(prefix="/testcases", tags=["Test Cases"])

client = AsyncOpenAI(api_key=settings.openai_api_key)


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
@router.post("/generate", response_model=List[TestCaseResponse])
async def generate_testcases(
    scenario_id: str = Query(...),
    count: int = Query(1, ge=1, le=20),
    complexity: str = Query("basic", regex="^(basic|medium|advanced)$"),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("executions")),
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
    scenario = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": user_email}
    )
    if not scenario:
        raise HTTPException(404, "Scenario not found.")

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
    used_tc = sub["usage"].get("testcases_used", 0)
    tc_limit = sub["limits"].get("testcases_limit")

    if tc_limit is not None:
        remaining_tc = max(tc_limit - used_tc, 0)
    else:
        remaining_tc = count  # effectively unlimited

    allowed = min(count, remaining_tc)

    if allowed <= 0:
        raise HTTPException(
            403,
            f"Testcase generation limit reached. Used {used_tc}/{tc_limit}.",
        )

    # -------------------------------------
    # 3) StepMapper: scenario steps → structured
    # -------------------------------------
    mapper = StepMapper()
    nl_steps = scenario.get("steps", [])

    generated_cases: List[TestCaseResponse] = []

    for _ in range(allowed):
        testcase_id = await get_next_sequence("testcase_id", "TC")

        structured_steps_dicts = [
            mapper.to_structured(step) for step in nl_steps
        ]
        structured_steps = [TestStep(**s) for s in structured_steps_dicts]

        # Generate Playwright code from structured steps
        code = generate_playwright_test(structured_steps)

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

    if scenario_id:
        filter_q["scenario_id"] = scenario_id

    if project_id:
        filter_q["project_id"] = project_id

    cursor = db["testcases"].find(filter_q)

    results: List[TestCaseResponse] = []
    async for doc in cursor:
        doc.pop("_id", None)
        doc["steps"] = [TestStep(**s) for s in doc.get("steps", [])]
        results.append(TestCaseResponse(**doc))

    return results
