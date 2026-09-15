import asyncio
import json
import logging
from datetime import datetime, timezone
from app.services.playwright_runner import execute_playwright_test
from app.services.subscription_services import increment_usage
from app.db.connection import db
# from app.utils.redis_client import redis_client
from redis.asyncio import Redis
from app.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

EXECUTION_QUEUE_KEY = "test_execution_queue"

# Create proper async Redis client
redis_client = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    username=settings.redis_username,
    password=settings.redis_password,
    # ssl=True,                   # REQUIRED for Redis Cloud
    decode_responses=False,     # BLPOP requires bytes
)

# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------

async def _run_manual(job):
    """
    Manual execution: mark execution as passed with no steps.
    """
    execution_id = job["execution_id"]
    end = datetime.now(timezone.utc)

    await db["executions"].update_one(
        {"execution_id": execution_id},
        {"$set": {
            "status": "passed",
            "completed_at": end.isoformat(),
            "duration_ms": 0,
            "step_results": [],
            "logs": {"message": "Manual execution completed"}
        }}
    )
    return "passed"


async def _run_cloud(job):
    """
    Placeholder for integration with a cloud execution provider:
    - BrowserStack
    - Sauce Labs
    - LambdaTest
    """
    execution_id = job["execution_id"]
    await db["executions"].update_one(
        {"execution_id": execution_id},
        {"$set": {"status": "error", "logs.error": "Cloud runner not implemented"}}
    )
    return "error"


async def _mark_failed(job, error_message):
    execution_id = job.get("execution_id")
    await db["executions"].update_one(
        {"execution_id": execution_id},
        {"$set": {"status": "error", "logs.error": error_message}}
    )


async def worker_loop():
    if not settings.features.native_execution:
        logger.info("Execution disabled; worker will not consume queued jobs.")
        return

    logger.info("🚀 Worker started. Listening for jobs...")

    while True:
        try:
            # ASYNC REDIS — MUST AWAIT
            job_data = await redis_client.brpop(EXECUTION_QUEUE_KEY, timeout=5)

            if not job_data:
                await asyncio.sleep(0.2)
                continue

            # job_data = [b'queue_name', b'json_payload']
            _, raw_payload = job_data

            # Decode Redis bytes → string → dict
            job = json.loads(raw_payload.decode("utf-8"))

            execution_id = job.get("execution_id")
            user_id = job.get("user_identifier")

            logger.info(f"📥 Worker picked job {execution_id}")

            # Pick runner type
            runner_type = job.get("runner_type", "playwright-local")

            try:
                if runner_type == "playwright-local":
                    result = await execute_playwright_test(job, db)

                elif runner_type == "playwright-cloud":
                    result = await _run_cloud(job)

                elif runner_type == "manual":
                    result = await _run_manual(job)

                else:
                    raise Exception(f"Unknown runner_type: {runner_type}")

            except Exception as e:
                logger.error(f"❌ Worker job failed: {e}")
                await _mark_failed(job, str(e))
                continue

            # Increment usage
            try:
                await increment_usage(user_id, "executions_used")
            except Exception as e:
                logger.error(f"⚠️ Failed to increment usage: {e}")

            logger.info(f"✅ Execution {execution_id} completed: {result}")

        except Exception as e:
            logger.error(f"🔥 Worker loop crash: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.info("🔥 Starting Execution Worker process...")
    asyncio.run(worker_loop())
