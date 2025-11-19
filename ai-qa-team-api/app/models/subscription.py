from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from app.app_config.plan_limits import PLAN_LIMITS

class UsageModel(BaseModel):
    projects_used: int = 0
    stories_used: int = 0
    scenarios_used: int = 0
    executions_used: int = 0
    team_members_used: int = 0
    ai_gen_used: int = 0

class LimitModel(BaseModel):
    projects_limit: int = 0
    stories_limit: int = 0
    scenarios_limit: int = 0
    executions_limit: int = 0
    team_members_limit: int = 0
    ai_gen_limit: Optional[int] = 0

class Subscription(BaseModel):
    plan: Literal["free", "pro", "enterprise"] = "free"
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiry_date: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    status: Literal["active", "expired", "cancelled"] = "active"
    provider: Optional[str] = "Manual"
    payment_id: Optional[str] = None
    # ✅ Usage tracking per feature
    usage: UsageModel = Field(default_factory=UsageModel)
    limits: LimitModel = Field(default_factory=LimitModel)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()  # ✅ ensures proper JSON serialization
        }

    def apply_plan_defaults(self):
        """Apply plan-specific limits from global PLAN_LIMITS"""
        plan_data = PLAN_LIMITS.get(self.plan, PLAN_LIMITS["free"])
        self.limits = LimitModel(**{
            "stories_limit": plan_data["stories_limit"],
            "scenarios_limit": plan_data["scenarios_limit"],
            "executions_limit": plan_data["executions_limit"],
            "team_members_limit": plan_data["team_members_limit"],
            "ai_gen_limit": plan_data["ai_gen_limit"],
        })

    def upgrade_to(self, plan: str) -> "Subscription":
        """Return a new Subscription instance with updated plan and limits."""
        now = datetime.now(timezone.utc)
        if plan not in PLAN_LIMITS:
            raise ValueError(f"Invalid plan name: {plan}")
        
        limits = PLAN_LIMITS[plan]
        
        return Subscription(
            plan=plan,
            start_date=now,
            expiry_date=now + timedelta(days=30),
            status="active",
            limits=LimitModel(**limits),
            provider=self.provider or "manual",
            usage=UsageModel() 
        )
