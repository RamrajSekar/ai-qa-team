from fastapi import APIRouter, HTTPException, Depends, Query
from app.db.connection import db
from app.routes.auth_routes import get_current_user
from app.services.story_service import get_next_sequence
from app.ai.prompts import generate_testcase_prompt
from app.models.test_case_model import TestCaseResponse
from app.utils.subscription_dependency import subscription_required
from app.services.subscription_services import get_subscription, increment_usage
from app.services.test_generator import generate_playwright_test
from app.config import settings
from openai import AsyncOpenAI
import json
from datetime import datetime, timezone
from typing import Optional, List

router = APIRouter(prefix="/testcases", tags=["Test Cases"])

client = AsyncOpenAI(api_key=settings.openai_api_key)

# Purpose (MVP):
# Converts scenario → JSON test structure
# No Playwright code generation
# Used by AI Test Generator Agent
@router.post("/generate", response_model=TestCaseResponse)
async def generate_testcase(
    scenario_id: str = Query(...),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("executions"))
):
    """
    Generate a single test case from a scenario.
    - Checks subscription execution limits
    - Creates sequential testcase_id (TC001)
    - Copies scenario steps -> testcase steps
    - Generates a Playwright test code block
    """

    user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")
    user_email = current_user.get("email")

    # ---------------------------------------------
    # 1) Validate scenario exists & belongs to user
    # ---------------------------------------------
    scenario = await db["scenarios"].find_one(
        {"scenario_id": scenario_id, "created_by": user_email}
    )

    if not scenario:
        raise HTTPException(404, "Scenario not found or access denied.")

    # ---------------------------------------------
    # 2) Validate subscription execution usage
    # ---------------------------------------------
    sub = await get_subscription(user_id)
    used_exec = sub["usage"].get("executions_used", 0)
    limit_exec = sub["limits"].get("executions_limit")

    if limit_exec is not None and used_exec + 1 > limit_exec:
        raise HTTPException(
            403,
            f"Execution limit reached. Used {used_exec}/{limit_exec}."
        )

    # ---------------------------------------------
    # 3) Generate sequential test case ID
    # ---------------------------------------------
    testcase_id = await get_next_sequence("testcase_id", "TC")

    # ---------------------------------------------
    # 4) Normalize steps from scenario -> testcase
    # ---------------------------------------------
    testcase_steps = []
    for s in scenario.get("steps", []):
        testcase_steps.append({
            "step_id": s["step_id"],
            "category": s.get("category", "General"),
            "action": s.get("action", ""),
            "expected": s.get("expected", "")
        })

    # ---------------------------------------------
    # 5) Generate code (Playwright stub)
    # ---------------------------------------------
    code = generate_playwright_test(scenario)

    # ---------------------------------------------
    # 6) Build final testcase document
    # ---------------------------------------------
    doc = {
        "testcase_id": testcase_id,
        "scenario_id": scenario_id,
        "project_id": scenario["project_id"],
        "title": scenario["title"],
        "description": scenario.get("description", ""),
        "steps": testcase_steps,
        "code": code,
        "status": "generated",
        "created_by": user_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await db["testcases"].insert_one(doc)
    doc["_id"] = result.inserted_id

    # Increment execution usage
    await increment_usage(user_id, "executions_used")

    return TestCaseResponse(**doc)

# GET single testcase by testcase_id
@router.get("/testcases/{testcase_id}", response_model=TestCaseResponse)
async def get_testcase(
    testcase_id: str,
    current_user=Depends(get_current_user)
):
    doc = await db["testcases"].find_one({"testcase_id": testcase_id})
    if not doc:
        raise HTTPException(404, "Testcase not found")

    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return TestCaseResponse(**doc)

# GET all testcases for a scenario
@router.get("/testcases", response_model=List[TestCaseResponse])
async def list_testcases(
    scenario_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("scenarios"))
):
    filter_q = {}

    if scenario_id:
        filter_q["scenario_id"] = scenario_id

    if project_id:
        filter_q["project_id"] = project_id

    cursor = db["testcases"].find(filter_q)

    results = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        results.append(TestCaseResponse(**doc))

    return results
