# Centralized plan configuration for usage and limits
PLAN_LIMITS = {
    "free": {
        "projects_limit": 1,
        "stories_limit": 5,
        "scenarios_limit": 10,
        "executions_limit": 20,
        "team_members_limit": 2,
        "ai_gen_limit": 25,
        # One Free allowance shared across all complexities.
        "testcases_limit": 10,
        "testcases_basic_limit": 10,
        "testcases_medium_limit": 10,
        "testcases_advanced_limit": 10,
        "description": "For individuals or small teams evaluating the platform."      
    },
    "pro": {
        "projects_limit": 10,
        "stories_limit": 100,
        "scenarios_limit": 200,
        "executions_limit": 1000,
        "team_members_limit": 5,
        "ai_gen_limit": 500,
        "testcases_basic_limit": 500,
        "testcases_medium_limit": 200,
        "testcases_advanced_limit": 100,
        "description": "For growing QA teams needing collaboration and CI/CD integration."
    },
    "enterprise": {
        "projects_limit": 1000,
        "stories_limit": 1000,
        "scenarios_limit": 2000,
        "testcases_basic_limit": 9999,
        "testcases_medium_limit": 9999,
        "testcases_advanced_limit": 9999,
        "executions_limit": 10000,
        "team_members_limit": 20,
        "ai_gen_limit": 5000,
        "description": "For large-scale QA automation teams with custom support."
    }
}


SUPPORTED_PLANS = (*PLAN_LIMITS, "team", "business")


def plan_limits(plan):
    """Server-owned defaults; existing subscriptions keep their saved snapshot."""
    if plan in PLAN_LIMITS:
        return dict(PLAN_LIMITS[plan])
    if plan not in ("team", "business"):
        raise ValueError("Unsupported subscription plan.")
    from app.config import settings
    offer = getattr(settings.pricing, plan)
    return {"projects_limit": offer.projects_limit, "stories_limit": offer.stories_limit,
        "scenarios_limit": offer.scenarios_limit, "testcases_limit": offer.testcases_limit,
        **{f"testcases_{tier}_limit": offer.testcases_limit for tier in ("basic", "medium", "advanced")},
        "team_members_limit": offer.users_limit - 1,
        "managed_ai_credits_limit": offer.managed_ai_credits_limit,
        "byok_ai_requests_limit": offer.byok_ai_requests_limit,
        "ai_gen_limit": offer.managed_ai_credits_limit, "executions_limit": 0}
