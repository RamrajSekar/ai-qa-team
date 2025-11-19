# app/routes/execution_routes.py

from typing import List, Optional, Literal
from app.db.connection import db
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status

from app.models.test_execution_model import (
    TestExecutionResponse,
    BatchExecuteRequest,
)
from app.services.execution_engine import (
    queue_test_execution,
    fetch_execution_by_id,
    list_executions_for_user,
)
from app.services.subscription_services import get_subscription
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required

router = APIRouter(
    prefix="/execute",
    tags=["Test Execution"],
)


@router.post(
    "/testcase/{testcase_id}",
    response_model=TestExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_single_testcase(
    testcase_id: str,
    environment: Optional[str] = Query("qa", description="Environment like dev/qa/stage"),
    browser: Optional[str] = Query("chromium", description="Browser: chromium/firefox/webkit"),
    headed: bool = Query(False),
    runner_type: Literal["playwright-local", "playwright-cloud", "manual"] = Query(
        "playwright-local",
        description="Execution runner: local, cloud, manual"
    ),
    dataset: Optional[dict | str] = Body(
        None,
        description="Optional test data payload (dict) or named dataset key.",
    ),
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("executions")),
):
    """
    Enqueue the execution of a single testcase.
    Returns the queued execution record (status=queued).
    """

    try:
        user_identifier = (
            current_user.get("_id")
            or current_user.get("id")
            or current_user.get("email")
        )
        user_email = current_user.get("email")

        # For now, project_id and scenario_id must be looked up from testcase
        testcase = await db["testcases"].find_one({"testcase_id": testcase_id})
        if not testcase:
            raise HTTPException(status_code=404, detail="Testcase not found")

        project_id = testcase.get("project_id")
        scenario_id = testcase.get("scenario_id")
        story_id = testcase.get("story_id")

        if not project_id:
            raise HTTPException(400, "Testcase is missing project_id")

        execution = await queue_test_execution(
            user_identifier=user_identifier,
            project_id=project_id,
            testcase_id=testcase_id,
            story_id=story_id,
            scenario_id=scenario_id,
            triggered_by=user_email,
            environment=environment,
            browser=browser,
            headed=headed,
            dataset=dataset,
            runner_type=runner_type,
        )

        return execution

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue testcase execution: {str(e)}",
        )


@router.post(
    "/batch",
    response_model=List[TestExecutionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_batch_testcases(
    request: BatchExecuteRequest,
    current_user=Depends(get_current_user),
    runner_type: Literal["playwright-local", "playwright-cloud", "manual"] = Query(
        "playwright-local",
        description="Execution runner: local, cloud, manual"
    ),
    _: None = Depends(subscription_required("executions")),
):
    """
    Enqueue multiple testcases in one request (for later parallel workers).
    Enforces executions_limit at batch level.
    """

    user_identifier = (
        current_user.get("_id")
        or current_user.get("id")
        or current_user.get("email")
    )
    user_email = current_user.get("email")

    # Subscription check for batch size
    sub = await get_subscription(user_identifier)
    used_exec = sub["usage"].get("executions_used", 0)
    exec_limit = sub["limits"].get("executions_limit")

    if exec_limit is not None and used_exec + len(request.testcase_ids) > exec_limit:
        remaining = max(exec_limit - used_exec, 0)
        raise HTTPException(
            status_code=403,
            detail=(
                f"You only have {remaining} executions left on your plan, "
                f"but requested {len(request.testcase_ids)}."
            ),
        )

    results: List[TestExecutionResponse] = []

    for testcase_id in request.testcase_ids:
        testcase = await db["testcases"].find_one({"testcase_id": testcase_id})
        if not testcase:
            # skip or raise — here we choose to skip & log
            # You can change to raise if you prefer strict behavior
            continue

        project_id = testcase.get("project_id")
        scenario_id = testcase.get("scenario_id")
        story_id = testcase.get("story_id")

        exec_resp = await queue_test_execution(
            user_identifier=user_identifier,
            project_id=project_id,
            testcase_id=testcase_id,
            story_id=story_id,
            scenario_id=scenario_id,
            triggered_by=user_email,
            environment=request.environment,
            browser=request.browser,
            headed=request.headed,
            dataset=request.dataset,
            runner_type=runner_type,
        )
        results.append(exec_resp)

    return results


@router.get(
    "/{execution_id}",
    response_model=TestExecutionResponse,
)
async def get_execution(
    execution_id: str,
    current_user=Depends(get_current_user),
):
    """
    Get a single execution's status & result.
    """
    exec_doc = await fetch_execution_by_id(execution_id)
    if not exec_doc:
        raise HTTPException(status_code=404, detail="Execution not found")

    # simple ownership check: same user
    if exec_doc.triggered_by != current_user.get("email"):
        raise HTTPException(status_code=403, detail="Access denied")

    return exec_doc


@router.get(
    "/",
    response_model=List[TestExecutionResponse],
)
async def list_my_executions(
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user),
):
    """
    List executions for the logged-in user (for dashboard).
    """
    user_email = current_user.get("email")
    execs = await list_executions_for_user(user_email=user_email, skip=skip, limit=limit)
    return execs
