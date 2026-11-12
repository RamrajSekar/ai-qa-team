# app/routes/execution_routes.py

from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status

from app.db.connection import db
from app.models.test_execution_model import TestExecutionResponse, BatchExecuteRequest
from app.services.execution_engine import (
    queue_test_execution,
    fetch_execution_by_id,
    list_executions_for_user,
)
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required
from app.config import settings
from app.utils.feature_flags import feature_required

router = APIRouter(prefix="/execute", tags=["Test Execution"])


# ----------------------------------------------------------
# 1️⃣ Execute Single Test Case with PROJECT-SPECIFIC ENV
# ----------------------------------------------------------
@router.post(
    "/testcase/{testcase_id}",
    dependencies=[Depends(feature_required("native_execution"))],
    include_in_schema=settings.features.native_execution,
    response_model=TestExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_single_testcase(
    testcase_id: str,

    env_type: str = Query("qa", description="Environment type: dev/qa/staging/prod"),
    role: Optional[str] = Query(None, description="Role: admin/qa/customer"),

    browser: Optional[str] = Query("chromium"),
    headed: bool = Query(False),

    runner_type: Literal["playwright-local", "playwright-cloud", "manual"] =
        Query("playwright-local"),

    dataset: Optional[dict | str] = Body(None),

    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("executions")),
):
    """Run a single testcase using project-specific environment."""

    user_email = current_user.get("email")

    # Load the testcase
    testcase = await db["testcases"].find_one({"testcase_id": testcase_id})
    if not testcase:
        raise HTTPException(404, "Testcase not found")

    project_id = testcase.get("project_id")
    scenario_id = testcase.get("scenario_id")
    story_id = testcase.get("story_id")

    # ----------------------------------------------
    # PROJECT-SPECIFIC ENVIRONMENT LOOKUP
    # ----------------------------------------------
    env_doc = await db["environments"].find_one({
        "project_id": project_id,
        "env_type": env_type.lower(),
        "created_by": user_email,
    })

    if not env_doc:
        raise HTTPException(
            404,
            f"No environment found for project {project_id} with env_type '{env_type}'"
        )

    # ----------------------------------------------
    # Role-based credential lookup
    # ----------------------------------------------
    selected_credentials = None

    if role:
        for cred in env_doc.get("credentials", []):
            if cred.get("role") == role:
                selected_credentials = cred
                break

        if not selected_credentials:
            raise HTTPException(
                400,
                f"Role '{role}' not found in environment {env_doc.get('name')}"
            )

    # ----------------------------------------------
    # Enqueue Execution
    # ----------------------------------------------
    user_identifier = user_email

    execution = await queue_test_execution(
        user_identifier=user_identifier,
        project_id=project_id,
        testcase_id=testcase_id,
        story_id=story_id,
        scenario_id=scenario_id,
        triggered_by=user_email,

        env_type=env_type,
        environment_doc=env_doc,
        credentials=selected_credentials,
        role=role,

        browser=browser,
        headed=headed,
        dataset=dataset,
        runner_type=runner_type,
    )

    return execution


# ----------------------------------------------------------
# 2️⃣ Batch Execution (project-specific env)
# ----------------------------------------------------------
@router.post(
    "/batch",
    dependencies=[Depends(feature_required("native_execution"))],
    include_in_schema=settings.features.native_execution,
    response_model=List[TestExecutionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_batch_testcases(
    request: BatchExecuteRequest,

    env_type: str = Query("qa"),
    role: Optional[str] = Query(None),

    runner_type: Literal["playwright-local", "playwright-cloud", "manual"] =
        Query("playwright-local"),

    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("executions")),
):
    """Run multiple testcases using project-specific env."""

    results: List[TestExecutionResponse] = []
    user_email = current_user.get("email")
    user_identifier = user_email

    # We use first testcase to detect project_id
    if not request.testcase_ids:
        raise HTTPException(400, "No testcase ids provided")

    # Load project_id from first testcase
    first_testcase = await db["testcases"].find_one(
        {"testcase_id": request.testcase_ids[0]}
    )
    if not first_testcase:
        raise HTTPException(404, "First testcase not found")

    project_id = first_testcase.get("project_id")

    # Load project-specific environment
    env_doc = await db["environments"].find_one({
        "project_id": project_id,
        "env_type": env_type.lower(),
        "created_by": user_email,
    })

    if not env_doc:
        raise HTTPException(
            404,
            f"No environment found for project {project_id} with env_type '{env_type}'"
        )

    # Role-based credentials
    selected_credentials = None
    if role:
        for cred in env_doc.get("credentials", []):
            if cred.get("role") == role:
                selected_credentials = cred
                break
        if not selected_credentials:
            raise HTTPException(
                400,
                f"Role '{role}' not found in environment {env_doc.get('name')}"
            )

    # Run testcases
    for testcase_id in request.testcase_ids:

        testcase = await db["testcases"].find_one({"testcase_id": testcase_id})
        if not testcase:
            continue

        scenario_id = testcase.get("scenario_id")
        story_id = testcase.get("story_id")

        exec_resp = await queue_test_execution(
            user_identifier=user_identifier,
            project_id=project_id,
            testcase_id=testcase_id,
            story_id=story_id,
            scenario_id=scenario_id,
            triggered_by=user_email,

            env_type=env_type,
            environment_doc=env_doc,
            credentials=selected_credentials,
            role=role,

            browser=request.browser,
            headed=request.headed,
            dataset=request.dataset,
            runner_type=runner_type,
        )

        results.append(exec_resp)

    return results


# ----------------------------------------------------------
# 3️⃣ Fetch single execution
# ----------------------------------------------------------
@router.get("/{execution_id}", response_model=TestExecutionResponse)
async def get_execution(
    execution_id: str,
    current_user=Depends(get_current_user),
):
    exec_doc = await fetch_execution_by_id(execution_id)
    if not exec_doc:
        raise HTTPException(404, "Execution not found")

    if exec_doc.triggered_by != current_user.get("email"):
        raise HTTPException(403, "Access denied")

    return exec_doc


# ----------------------------------------------------------
# 4️⃣ List executions (dashboard)
# ----------------------------------------------------------
@router.get("", response_model=List[TestExecutionResponse], include_in_schema=False)
@router.get("/", response_model=List[TestExecutionResponse])
async def list_my_executions(
    skip: int = 0,
    limit: int = 20,
    complexity: Optional[str] = Query(
        None,
        description="Filter by testcase complexity: basic | medium | advanced",
    ),
    current_user=Depends(get_current_user),
):
    user_email = current_user.get("email")
    return await list_executions_for_user(
        user_email=user_email,
        skip=skip,
        limit=limit,
        complexity=complexity,
        **({"account_id": current_user["account_id"]} if current_user.get("account_id") else {}),
    )
