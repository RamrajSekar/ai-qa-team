# Centralized plan configuration for usage and limits
PLAN_LIMITS = {
    "free": {
        "stories_limit": 5,
        "scenarios_limit": 10,
        "executions_limit": 20,
        "team_members_limit": 1,
        "description": "For individuals or small teams evaluating the platform."
    },
    "pro": {
        "stories_limit": 100,
        "scenarios_limit": 200,
        "executions_limit": 1000,
        "team_members_limit": 5,
        "description": "For growing QA teams needing collaboration and CI/CD integration."
    },
    "enterprise": {
        "stories_limit": 1000,
        "scenarios_limit": 2000,
        "executions_limit": 10000,
        "team_members_limit": 20,
        "description": "For large-scale QA automation teams with custom support."
    }
}
