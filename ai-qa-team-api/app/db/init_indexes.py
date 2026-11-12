from app.db.connection import db
from app.config import settings


async def init_indexes():
    if settings.features.customer_accounts:
        # Enable only after the dry-run migration audit resolves duplicate identities.
        await db["users"].create_index("email", unique=True)
        await db["users"].create_index("account_id")
        await db["projects"].create_index("account_id")
        await db["account_invitations"].create_index([("account_id", 1), ("status", 1)])
    # Unique IDs
    await db["projects"].create_index("project_id", unique=True)
    await db["stories"].create_index("story_id", unique=True)
    await db["scenarios"].create_index("scenario_id", unique=True)
    await db["testcases"].create_index("testcase_id", unique=True)
    await db["executions"].create_index("execution_id", unique=True)
    await db["repositories"].create_index("repository_id", unique=True)
    await db["discovered_tests"].create_index("test_id", unique=True)
    await db["project_memberships"].create_index("membership_id", unique=True)
    await db["project_memberships"].create_index([("project_id", 1), ("email", 1)], unique=True)

    # Common filters
    await db["scenarios"].create_index([("story_id", 1), ("created_by", 1)])
    await db["testcases"].create_index([("scenario_id", 1), ("created_by", 1)])
    await db["testcases"].create_index([("project_id", 1), ("created_by", 1)])
    await db["executions"].create_index([("triggered_by", 1), ("started_at", -1)])
    await db["executions"].create_index([("project_id", 1), ("started_at", -1)])
    await db["repositories"].create_index([("project_id", 1), ("created_by", 1)])
    await db["discovered_tests"].create_index([
        ("project_id", 1), ("repository_id", 1), ("source_commit_sha", 1)
    ])
    await db["project_memberships"].create_index([("email", 1), ("status", 1)])
    await db["project_memberships"].create_index([("billing_owner", 1), ("counts_toward_limit", 1)])
    await db["ai_configurations"].create_index("project_id", unique=True)
    await db["encrypted_secrets"].create_index("credential_ref", unique=True)
    await db["encrypted_secrets"].create_index([("project_id", 1), ("credential_ref", 1)])
    await db["prompt_definitions"].create_index("prompt_key", unique=True)
    await db["ai_usage_records"].create_index("usage_id", unique=True)
    await db["ai_usage_records"].create_index([
        ("project_id", 1), ("user_id", 1), ("operation_type", 1), ("started_at", -1)
    ])
    await db["ai_usage_records"].create_index([("billing_owner", 1), ("billing_period_start", 1)])
    await db["ai_usage_records"].create_index([("account_id", 1), ("billing_period_start", 1)])
