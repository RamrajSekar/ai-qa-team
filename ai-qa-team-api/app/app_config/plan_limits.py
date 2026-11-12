# Centralized plan configuration for usage and limits
PLAN_LIMITS = {
    "free": {
        "projects_limit": 1,
        "stories_limit": 5,
        "scenarios_limit": 10,
        "executions_limit": 20,
        "team_members_limit": 2,
        "ai_gen_limit": 3,
        # 🆕 testcases per complexity
        "testcases_basic_limit": 10,
        "testcases_medium_limit": 0,
        "testcases_advanced_limit": 0,
        "description": "For individuals or small teams evaluating the platform."      
    },
    "pro": {
        "projects_limit": 10,
        "stories_limit": 100,
        "scenarios_limit": 200,
        "executions_limit": 1000,
        "team_members_limit": 5,
        "ai_gen_limit": 50,
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
        "ai_gen_limit": None,
        "description": "For large-scale QA automation teams with custom support."
    }
}
