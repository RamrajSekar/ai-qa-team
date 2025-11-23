from app.db.connection import db


async def init_indexes():
    # Unique IDs
    await db["projects"].create_index("project_id", unique=True)
    await db["stories"].create_index("story_id", unique=True)
    await db["scenarios"].create_index("scenario_id", unique=True)
    await db["testcases"].create_index("testcase_id", unique=True)
    await db["executions"].create_index("execution_id", unique=True)

    # Common filters
    await db["scenarios"].create_index([("story_id", 1), ("created_by", 1)])
    await db["testcases"].create_index([("scenario_id", 1), ("created_by", 1)])
    await db["testcases"].create_index([("project_id", 1), ("created_by", 1)])
    await db["executions"].create_index([("triggered_by", 1), ("started_at", -1)])
    await db["executions"].create_index([("project_id", 1), ("started_at", -1)])
