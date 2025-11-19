# app/services/execution_service.py

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal

from bson import ObjectId

from app.db.connection import db
from app.models.test_execution_model import (
    TestExecution,
    TestExecutionResponse,
    StepResult,
)
from app.services.subscription_services import increment_usage, get_subscription
from app.services.story_service import get_next_sequence
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)

EXECUTION_QUEUE_KEY = "test_execution_queue"


async def create_execution_record(
    *,
    project_id: str,
    testcase_id: str,
    triggered_by: str,
    story_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    environment: Optional[str] = None,
    browser: Optional[str] = None,
    headed: bool = False,
    dataset: Optional[dict | str] = None,
    runner_type: Literal["playwright-local", "playwright-cloud", "manual"] = "playwright-local",
) -> TestExecutionResponse:
    """
    Insert a new TestExecution document into MongoDB with status='queued'.
    Does NOT run the test, only creates the record.
    """
    execution_id = await get_next_sequence("execution_id", "EX")

    execution = TestExecution(
        execution_id=execution_id,
        project_id=project_id,
        story_id=story_id,
        scenario_id=scenario_id,
        testcase_id=testcase_id,
        status="queued",
        environment=environment,
        browser=browser,
        headed=headed,
        dataset=dataset,
        started_at=None,
        completed_at=None,
        duration_ms=None,
        triggered_by=triggered_by,
        runner_type=runner_type,
        step_results=[],
        logs={},
    )

    doc = execution.model_dump()
    result = await db["executions"].insert_one(doc)
    doc["_id"] = result.inserted_id

    logger.info(f"📥 Created execution record {execution_id} for testcase {testcase_id}")

    return TestExecutionResponse(
        id=str(doc["_id"]),
        execution_id=doc["execution_id"],
        project_id=doc["project_id"],
        story_id=doc.get("story_id"),
        scenario_id=doc.get("scenario_id"),
        testcase_id=doc["testcase_id"],
        status=doc["status"],
        environment=doc.get("environment"),
        browser=doc.get("browser"),
        headed=doc["headed"],
        dataset=doc.get("dataset"),
        started_at=doc.get("started_at"),
        completed_at=doc.get("completed_at"),
        duration_ms=doc.get("duration_ms"),
        triggered_by=doc["triggered_by"],
        runner_type=doc["runner_type"],
        step_results=[],
        logs={},
    )


async def queue_test_execution(
    *,
    user_identifier: str,
    project_id: str,
    testcase_id: str,
    triggered_by: str,
    story_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    environment: Optional[str] = None,
    browser: Optional[str] = None,
    headed: bool = False,
    dataset: Optional[dict | str] = None,
    runner_type: Literal["playwright-local", "playwright-cloud", "manual"] = "playwright-local",
) -> TestExecutionResponse:
    """
    High-level service:
      1) Validates subscription limits (executions_limit)
      2) Creates execution record (status=queued)
      3) Enqueues job into Redis for worker to pick up.
    """

    # --- Subscription check for executions_limit ---
    sub = await get_subscription(user_identifier)
    if not sub:
        raise ValueError("No subscription found for this user")

    used_exec = sub["usage"].get("executions_used", 0)
    exec_limit = sub["limits"].get("executions_limit")

    if exec_limit is not None and used_exec >= exec_limit:
        raise ValueError(
            f"Execution limit reached ({used_exec}/{exec_limit}). Please upgrade your plan."
        )

    # --- Create execution record in Mongo ---
    execution_response = await create_execution_record(
        project_id=project_id,
        testcase_id=testcase_id,
        story_id=story_id,
        scenario_id=scenario_id,
        triggered_by=triggered_by,
        environment=environment,
        browser=browser,
        headed=headed,
        dataset=dataset,
        runner_type=runner_type,
    )
    # ["execution_id", "testcase_id", "project_id","scenario_id", "browser", "environment"]
    # --- Push job into Redis queue ---
    payload = {
        "execution_id": execution_response.execution_id,
        "project_id": execution_response.project_id,
        "scenario_id": execution_response.scenario_id,
        "testcase_id": execution_response.testcase_id,
        "browser": execution_response.browser,
        "headed": execution_response.headed,
        "environment": execution_response.environment,
        "mongo_id": execution_response.id,
        "user_identifier": user_identifier,
    }

    try:
        redis_client.rpush(EXECUTION_QUEUE_KEY, json.dumps(payload))
        logger.info(
            f"🚀 Enqueued execution {execution_response.execution_id} to Redis queue"
        )
    except Exception as e:
        logger.error(f"❌ Failed to enqueue execution in Redis: {e}")
        # Optional: mark execution as error in Mongo
        await db["executions"].update_one(
            {"execution_id": execution_response.execution_id},
            {"$set": {"status": "error", "logs.redis_error": str(e)}},
        )
        raise

    return execution_response


async def fetch_execution_by_id(execution_id: str) -> Optional[TestExecutionResponse]:
    """
    Fetch an execution by execution_id and convert to response model.
    """
    doc = await db["executions"].find_one({"execution_id": execution_id})
    if not doc:
        return None

    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)

    # Normalize step_results to StepResult
    step_results_raw: List[Dict[str, Any]] = doc.get("step_results", [])
    step_results: List[StepResult] = [StepResult(**s) for s in step_results_raw]

    return TestExecutionResponse(
        id=doc["id"],
        execution_id=doc["execution_id"],
        project_id=doc["project_id"],
        story_id=doc.get("story_id"),
        scenario_id=doc.get("scenario_id"),
        testcase_id=doc["testcase_id"],
        status=doc["status"],
        environment=doc.get("environment"),
        browser=doc.get("browser"),
        headed=doc.get("headed"),
        dataset=doc.get("dataset"),
        started_at=doc.get("started_at"),
        completed_at=doc.get("completed_at"),
        duration_ms=doc.get("duration_ms"),
        triggered_by=doc["triggered_by"],
        runner_type=doc["runner_type"],
        step_results=step_results,
        logs=doc.get("logs", {}),
    )


async def list_executions_for_user(
    user_email: str,
    skip: int = 0,
    limit: int = 20,
) -> List[TestExecutionResponse]:
    """
    List executions triggered by this user (for dashboard).
    """
    cursor = (
        db["executions"]
        .find({"triggered_by": user_email})
        .sort("started_at", -1)
        .skip(skip)
        .limit(limit)
    )

    results: List[TestExecutionResponse] = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        step_results_raw: List[Dict[str, Any]] = doc.get("step_results", [])
        step_results: List[StepResult] = [StepResult(**s) for s in step_results_raw]

        results.append(
            TestExecutionResponse(
                id=doc["id"],
                execution_id=doc["execution_id"],
                project_id=doc["project_id"],
                story_id=doc.get("story_id"),
                scenario_id=doc.get("scenario_id"),
                testcase_id=doc["testcase_id"],
                status=doc["status"],
                environment=doc.get("environment"),
                browser=doc.get("browser"),
                headed=doc.get("headed"),
                dataset=doc.get("dataset"),
                started_at=doc.get("started_at"),
                completed_at=doc.get("completed_at"),
                duration_ms=doc.get("duration_ms"),
                triggered_by=doc["triggered_by"],
                runner_type=doc["runner_type"],
                step_results=step_results,
                logs=doc.get("logs", {}),
            )
        )

    return results
