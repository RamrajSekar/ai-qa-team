from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
from typing import Optional, Literal
from app.models.subscription import Subscription

class OnboardingModel(BaseModel):
    onboarding_status: Literal["not_started", "in_progress", "completed"] = "not_started"
    current_step: int = 1
    steps: dict = {
        "project": False,
        "environment": False,
        "add_users": False,
        "test_import": False,
        "finish": False
    }
    context: dict = {
        "project_id": None,
        "environment_id": None
    }


class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    email: EmailStr
    password: Optional[str] = None
    provider: str = "local"  # local, google, github
    role: str = "admin"     # admin, lead, tester
    platform_role: Literal["OWNER", "ADMIN", "NONE"] = "NONE"
    onboarding: dict = Field(default_factory=lambda: OnboardingModel().model_dump())
    subscription: Subscription = Field(default_factory=Subscription)
    created_at: datetime = datetime.now(timezone.utc)
    
    # allows using 'id=' instead of '_id'

    # def mongo_dict(self):
    #     data = self.model_dump(by_alias=True)
    #     # FIX → Convert nested models manually
    #     data["subscription"] = self.subscription.model_dump()
    #     # data["onboarding"] = self.onboarding.model_dump()
    #     return data
    class Config:
        populate_by_name = True 
