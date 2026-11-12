from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from app.app_config.plan_limits import PLAN_LIMITS

class UsageModel(BaseModel):
    projects_used: int = 0
    stories_used: int = 0
    scenarios_used: int = 0
    testcases_used: int = 0
    executions_used: int = 0
    team_members_used: int = 0
    ai_gen_used: int = 0
    managed_ai_credits_used: int = 0
    byok_ai_requests_used: int = 0
    # 🆕 Testcase usage by complexity
    testcases_basic_used: int = 0
    testcases_medium_used: int = 0
    testcases_advanced_used: int = 0

class LimitModel(BaseModel):
    projects_limit: int = 0
    stories_limit: int = 0
    scenarios_limit: int = 0
    testcases_limit: int = 0
    executions_limit: int = 0
    team_members_limit: int = 0
    ai_gen_limit: Optional[int] = 0
    managed_ai_credits_limit: int = 0
    byok_ai_requests_limit: int = 0
    # 🆕 Testcase limits by complexity
    testcases_basic_limit: int = 0
    testcases_medium_limit: int = 0
    testcases_advanced_limit: int = 0

class Subscription(BaseModel):
    plan: Literal["free", "pro", "enterprise"] = "free"
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiry_date: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30)
    )
    status: Literal["active", "expired", "cancelled"] = "active"
    provider: Optional[str] = "Manual"
    payment_id: Optional[str] = None
    ai_allowance_version: Optional[int] = None
    ai_usage_period_start: Optional[datetime] = None
    ai_usage_period_end: Optional[datetime] = None

    usage: UsageModel = Field(default_factory=UsageModel)
    limits: LimitModel = Field(default_factory=LimitModel)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def apply_plan_defaults(self):
        """
        Automatically apply plan defaults only when limits are empty (all zeros).
        This prevents uninitialized limit values at signup.
        """
        plan_data = PLAN_LIMITS.get(self.plan, PLAN_LIMITS["free"])

        # Detect empty limits model
        if self.limits.projects_limit == 0 and self.limits.scenarios_limit == 0:
            self.limits = LimitModel(
                projects_limit=plan_data["projects_limit"],
                stories_limit=plan_data["stories_limit"],
                scenarios_limit=plan_data["scenarios_limit"],
                executions_limit=plan_data["executions_limit"],
                team_members_limit=plan_data["team_members_limit"],
                ai_gen_limit=plan_data["ai_gen_limit"],
                testcases_basic_limit=plan_data.get("testcases_basic_limit", 0),
                testcases_medium_limit=plan_data.get("testcases_medium_limit", 0),
                testcases_advanced_limit=plan_data.get("testcases_advanced_limit", 0),
            )

        from app.services.ai_allowances import configured_limits
        limits = configured_limits(self.plan)
        self.limits.managed_ai_credits_limit = limits["managed_ai_credits_limit"]
        self.limits.byok_ai_requests_limit = limits["byok_ai_requests_limit"]
