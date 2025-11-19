import json
import asyncio
from redis.asyncio import Redis
from app.db.connection import db
from app.services.playwright_runner import execute_playwright_test
from app.config import settings

QUEUE_KEY = "test_execution_queue"

# Create proper async Redis client
redis_client = Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    username=settings.redis_username,
    password=settings.redis_password,
    # ssl=True,                   # REQUIRED for Redis Cloud
    decode_responses=False,     # BLPOP requires bytes
)


async def worker_loop():
    print("🚀 Worker started. Listening for jobs...")

    while True:
        try:
            # ❗ brpop returns: [b'queue_name', b'json_data']
            result = await redis_client.brpop(QUEUE_KEY, timeout=5)

            if not result:
                await asyncio.sleep(0.25)
                continue

            _, task_bytes = result
            job = json.loads(task_bytes.decode("utf-8"))

            print(f"🎯 Worker picked job: {job['execution_id']}")
            print("📦 RAW JOB:", job)

            # Validate required keys
            required = ["execution_id", "testcase_id", "project_id", "scenario_id", "browser", "environment"]
            for r in required:
                if r not in job:
                    raise Exception(f"Missing required job field: {r}")
            headed = job.get("headed", False)
            runner_type = job.get("runner_type",)
            # Enforce safety
            if runner_type != "playwright-local":
                headed = False

            job["headed"] = headed
            # Execute test
            await execute_playwright_test(job, db)

        except Exception as e:
            print(f"🔥 Worker error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(worker_loop())
