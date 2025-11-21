from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal


class EnvironmentCredentials(BaseModel):
    role: str                      # admin, qa, customer, etc.
    username: str
    password: str
    notes: Optional[str] = None


class ProjectEnvironment(BaseModel):
    project_id: str                # NEW — project this environment belongs to
    env_id: str                    # ENV001
    env_type: Literal["local", "dev", "qa", "staging", "prod"] = "qa"

    base_url: str
    api_base_url: Optional[str] = None

    auth_type: Literal["none", "basic", "bearer"] = "none"
    auth_token: Optional[str] = None

    credentials: List[EnvironmentCredentials] = Field(default_factory=list)

    default_browser: Literal["chromium", "firefox", "webkit"] = "chromium"
    default_headed: bool = False
    default_timeout_ms: int = 10000

    variables: Dict[str, Any] = Field(default_factory=dict)


class ProjectEnvironmentResponse(ProjectEnvironment):
    id: str
