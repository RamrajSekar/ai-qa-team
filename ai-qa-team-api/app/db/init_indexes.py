from app.db.connection import db
from app.config import settings
from pymongo import IndexModel
import asyncio


async def init_indexes():
    # Batch each collection into one command, with bounded parallel startup work.
    indexes = {}
    def add(collection, keys, **options):
        indexes.setdefault(collection, []).append(IndexModel(keys, **options))

    if settings.features.customer_accounts:
        # Enable only after the dry-run migration audit resolves duplicate identities.
        add("users", "email", unique=True)
        add("users", "account_id")
        add("projects", "account_id")
        add("account_invitations", [("account_id", 1), ("status", 1)])
    # Unique IDs
    add("projects", "project_id", unique=True)
    add("stories", "story_id", unique=True)
    add("scenarios", "scenario_id", unique=True)
    add("testcases", "testcase_id", unique=True)
    add("executions", "execution_id", unique=True)
    add("repositories", "repository_id", unique=True)
    add("discovered_tests", "test_id", unique=True)
    add("project_memberships", "membership_id", unique=True)
    add("project_memberships", [("project_id", 1), ("email", 1)], unique=True)

    # Project catalogs: match bounded list filters and ordering.
    add("stories", "project_id")
    add("scenarios", [("project_id", 1), ("scenario_id", 1)])
    add("testcases", [("project_id", 1), ("testcase_id", 1)])
    add("environments", "project_id")

    # Common filters
    add("scenarios", [("story_id", 1), ("created_by", 1)])
    add("testcases", [("scenario_id", 1), ("created_by", 1)])
    add("testcases", [("project_id", 1), ("created_by", 1)])
    add("executions", [("triggered_by", 1), ("started_at", -1)])
    add("executions", [("project_id", 1), ("started_at", -1)])
    add("repositories", [("project_id", 1), ("created_by", 1)])
    add("discovered_tests", [
        ("project_id", 1), ("repository_id", 1), ("source_commit_sha", 1)
    ])
    add("project_memberships", [("email", 1), ("status", 1)])
    add("project_memberships", [("billing_owner", 1), ("counts_toward_limit", 1)])
    add("ai_configurations", "project_id", unique=True)
    add("encrypted_secrets", "credential_ref", unique=True)
    add("encrypted_secrets", [("project_id", 1), ("credential_ref", 1)])
    add("prompt_definitions", "prompt_key", unique=True)
    add("ai_usage_records", "usage_id", unique=True)
    add("ai_usage_records", [
        ("project_id", 1), ("user_id", 1), ("operation_type", 1), ("started_at", -1)
    ])
    add("ai_usage_records", [("billing_owner", 1), ("billing_period_start", 1)])
    add("ai_usage_records", [("account_id", 1), ("billing_period_start", 1)])
    add("jira_import_previews", "expires_at", expireAfterSeconds=0)

    for collection in ("jira_oauth_flows", "jira_oauth_grants"):
        add(collection, "expires_at", expireAfterSeconds=0)

    add("requirement_contexts", [("project_id", 1), ("story_id", 1), ("record_type", 1), ("created_at", -1)])

    add("product_knowledge_versions", [("scope_project_id", 1), ("record_type", 1)])
    slots = asyncio.Semaphore(4)
    async def create(collection, models):
        async with slots:
            await db[collection].create_indexes(models)
    # Await every result before startup; failures must still prevent serving.
    results = await asyncio.gather(*(create(name, models) for name, models in indexes.items()), return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            raise result
