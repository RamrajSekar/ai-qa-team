from app.db.connection import db

async def sync_usage(email: str) -> dict:
    """Recalculate all usage counters for a user."""

    counts = {
        "projects_used": await db["projects"].count_documents({"created_by": email}),
        "stories_used": await db["stories"].count_documents({"created_by": email}),
        "scenarios_used": await db["scenarios"].count_documents({"created_by": email}),
        "testcases_used": await db["testcases"].count_documents({"created_by": email}),
        "executions_used": await db["executions"].count_documents({"created_by": email}),
        "team_members_used": await db["project_memberships"].count_documents({
            "billing_owner": email, "counts_toward_limit": True,
        }),
        "ai_gen_used": await db["ai_generations"].count_documents({"created_by": email}),
        "testcases_basic_used": await db["testcases"].count_documents({"created_by": email, "level": "basic"}),
        "testcases_medium_used": await db["testcases"].count_documents({"created_by": email, "level": "medium"}),
        "testcases_advanced_used": await db["testcases"].count_documents({"created_by": email, "level": "advanced"}),
    }

    # Update user document
    await db["users"].update_one(
        {"email": email},
        {"$set": {"subscription.usage": counts}}
    )

    return counts
