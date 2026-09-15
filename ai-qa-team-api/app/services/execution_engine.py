# app/services/execution_service.py

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Literal, Dict, Any

from bson import ObjectId

from app.db.connection import db
from app.models.test_execution_model import (
    TestExecution,
    TestExecutionResponse,
)
from app.services.subscription_services import get_subscription, increment_usage
from app.services.story_service import get_next_sequence
from app.utils.redis_client import redis_client
from app.utils.feature_flags import require_features

logger = logging.getLogger(__name__)

EXECUTION_QUEUE_KEY = 'test_execution_queue'


# ---------------------------------------------------------
# JSON / BSON helper
# ---------------------------------------------------------
def json_safe(value: Any) -> Any:
    """Recursively convert Mongo/BSON types to JSON-serializable values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items() if k != '_id'}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value


# ---------------------------------------------------------
# Create execution record in MongoDB
# ---------------------------------------------------------
async def create_execution_record(
    *,
    project_id: str,
    testcase_id: str,
    triggered_by: str,

    env_type: str,
    environment_doc: Dict[str, Any],
    credentials: Optional[Dict[str, Any]] = None,
    role: Optional[str] = None,

    browser: Optional[str] = None,
    headed: bool = False,
    dataset: Optional[dict | str] = None,
    runner_type: Literal['playwright-local', 'playwright-cloud', 'manual'],

    story_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    complexity: Optional[str] = None,
) -> TestExecutionResponse:
    """
    Create a TestExecution document with status='queued' and store in Mongo.
    Does NOT execute the test.
    """

    require_features("native_execution")
    execution_id = await get_next_sequence('execution_id', 'EX')

    # Normalize dataset
    if isinstance(dataset, str):
        try:
            dataset = json.loads(dataset)
        except Exception:
            dataset = {'raw': dataset}

    # Environment defaults
    final_env_type = environment_doc.get('env_type') or env_type
    env_id = environment_doc.get('env_id')
    base_url = environment_doc.get('base_url')
    api_base_url = environment_doc.get('api_base_url')
    env_variables = environment_doc.get('variables', {}) or {}
    auth_type = environment_doc.get('auth_type')
    auth_token = environment_doc.get('auth_token')

    final_browser = browser or environment_doc.get('default_browser', 'chromium')
    final_headed = headed if headed is True else environment_doc.get('default_headed', False)

    # Clean env + credentials so we don't store ObjectIds inside execution docs
    env_clean = json_safe(environment_doc)
    creds_clean = json_safe(credentials) if credentials else None

    execution = TestExecution(
        execution_id=execution_id,
        project_id=project_id,
        story_id=story_id,
        scenario_id=scenario_id,
        testcase_id=testcase_id,
        status='queued',

        env_type=final_env_type,
        env_id=env_id,
        role=role,
        environment_doc=env_clean,
        credentials=creds_clean,
        base_url=base_url,
        api_base_url=api_base_url,
        env_variables=env_variables,
        auth_type=auth_type,
        auth_token=auth_token,

        browser=final_browser,
        headed=final_headed,
        dataset=dataset,
        started_at=None,
        completed_at=None,
        duration_ms=None,
        complexity=complexity,
        triggered_by=triggered_by,
        runner_type=runner_type,
        step_results=[],
        logs={},
    )

    # Store as plain dict
    doc = execution.model_dump()
    result = await db['executions'].insert_one(doc)

    # Build a clean response for API
    response_doc: Dict[str, Any] = {
        'id': str(result.inserted_id),
        'execution_id': execution.execution_id,
        'project_id': execution.project_id,
        'story_id': execution.story_id,
        'scenario_id': execution.scenario_id,
        'testcase_id': execution.testcase_id,
        'status': execution.status,
        'env_type': execution.env_type,
        'env_id': execution.env_id,
        'role': execution.role,
        'environment_doc': execution.environment_doc,
        'complexity': execution.complexity,
        'credentials': execution.credentials,
        'base_url': execution.base_url,
        'api_base_url': execution.api_base_url,
        'env_variables': execution.env_variables,
        'auth_type': execution.auth_type,
        'auth_token': execution.auth_token,
        'browser': execution.browser,
        'headed': execution.headed,
        'dataset': execution.dataset,
        'started_at': execution.started_at,
        'completed_at': execution.completed_at,
        'duration_ms': execution.duration_ms,
        'triggered_by': execution.triggered_by,
        'runner_type': execution.runner_type,
        'step_results': [],
        'logs': {},
    }

    return TestExecutionResponse(**response_doc)


# ---------------------------------------------------------
# Queue execution into Redis for worker
# ---------------------------------------------------------
async def queue_test_execution(
    *,
    user_identifier: str,
    project_id: str,
    testcase_id: str,
    triggered_by: str,
    story_id: Optional[str],
    scenario_id: Optional[str],

    env_type: str,
    environment_doc: Dict[str, Any],
    credentials: Optional[Dict[str, Any]],
    role: Optional[str],

    browser: Optional[str],
    headed: bool,
    dataset: Optional[dict | str],
    complexity: Optional[str]='basic',
    runner_type: Literal['playwright-local', 'playwright-cloud', 'manual'] = 'playwright-local',
) -> TestExecutionResponse:
    """
    High-level orchestration:
      1) Validates subscription usage
      2) Creates a TestExecution record
      3) Pushes a job into Redis for the worker
    """

    require_features("native_execution")

    # Subscription check
    sub = await get_subscription(user_identifier)
    if not sub:
        raise ValueError('Subscription not found')

    used = sub['usage'].get('executions_used', 0)
    limit = sub['limits'].get('executions_limit')

    if limit is not None and used >= limit:
        raise ValueError(f'Execution limit reached ({used}/{limit})')

      # ------------------------------------------
    # Load testcase to get complexity
    # ------------------------------------------
    testcase = await db["testcases"].find_one({"testcase_id": testcase_id})
    if not testcase:
        raise ValueError(f"Testcase {testcase_id} not found")

    testcase_complexity = testcase.get("complexity", complexity)

    # Create execution record
    execution_response = await create_execution_record(
        project_id=project_id,
        testcase_id=testcase_id,
        triggered_by=triggered_by,
        story_id=story_id,
        scenario_id=scenario_id,
        env_type=env_type,
        environment_doc=environment_doc,
        credentials=credentials,
        role=role,
        browser=browser,
        headed=headed,
        dataset=dataset,
        runner_type=runner_type,
        complexity=testcase_complexity,
    )

    # Prepare JSON-safe payload for worker
    env_clean = json_safe(environment_doc)
    creds_clean = json_safe(credentials) if credentials else None
    dataset_clean = json_safe(dataset)

    payload: Dict[str, Any] = {
        'execution_id': execution_response.execution_id,
        'mongo_id': execution_response.id,
        'project_id': project_id,
        'testcase_id': testcase_id,
        'story_id': story_id,
        'scenario_id': scenario_id,
        'env_type': env_type,
        'role': role,
        'environment': env_clean,       # worker / runner reads this
        'credentials': creds_clean,
        'browser': browser,
        'headed': headed,
        'dataset': dataset_clean,
        'runner_type': runner_type,
        'user_identifier': user_identifier,
        'queued_at': datetime.now(timezone.utc).isoformat(),
    }

    # Validate serializability
    json.dumps(payload)

    # Push to Redis (sync client)
    redis_client.rpush(EXECUTION_QUEUE_KEY, json.dumps(payload))

    # Increment usage counter (best-effort)
    try:
        await increment_usage(user_identifier, 'executions_used')
    except Exception as e:
        logger.error(f'⚠️ Failed to increment usage: {e}')

    return execution_response


# ---------------------------------------------------------
# Fetch single execution
# ---------------------------------------------------------
async def fetch_execution_by_id(execution_id: str) -> Optional[TestExecutionResponse]:
    """
    Fetch a single execution and map directly into TestExecutionResponse.
    """
    doc = await db['executions'].find_one({'execution_id': execution_id})
    if not doc:
        return None

    doc['id'] = str(doc['_id'])
    doc.pop('_id', None)

    # Older records may have `environment` as string; it's ignored by model.
    # `environment_doc` is the new structured field.

    return TestExecutionResponse(**doc)


# ---------------------------------------------------------
# List executions for a user (dashboard)
# ---------------------------------------------------------
async def list_executions_for_user(
    user_email: str,
    skip: int = 0,
    limit: int = 20,
    complexity: Optional[str] = None,
) -> List[TestExecutionResponse]:
    """
    List executions triggered by this user (for dashboard),
    optionally filtered by testcase complexity.
    """
    query: Dict[str, Any] = {"triggered_by": user_email}
    if complexity:
        query["complexity"] = complexity

    cursor = (
        db['executions']
        .find(query)
        .sort('started_at', -1)
        .skip(skip)
        .limit(limit)
    )

    results: List[TestExecutionResponse] = []
    async for doc in cursor:
        doc['id'] = str(doc['_id'])
        doc.pop('_id', None)
        results.append(TestExecutionResponse(**doc))

    return results
