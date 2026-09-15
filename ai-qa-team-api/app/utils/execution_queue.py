import json
from typing import Dict, Any
from app.utils.redis_client import redis_client
from app.utils.feature_flags import require_features

EXECUTION_QUEUE_KEY = 'test_execution_queue'

# Not used yet
def enqueue_execution_job(job: Dict[str, Any]) -> None:
    """
    Push a new execution job into Redis.

    This is a *sync* function because redis_client is sync in your project.
    FastAPI async endpoints can safely call it.
    """
    require_features("native_execution")
    payload = json.dumps(job, default=str)
    redis_client.lpush(EXECUTION_QUEUE_KEY, payload)
