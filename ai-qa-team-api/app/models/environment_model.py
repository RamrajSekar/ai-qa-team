from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal


class EnvironmentCredentials(BaseModel):
    role: str                      # admin, qa, customer, etc.
    username: str
    password: str = Field(default="", repr=False)
    credential_id: Optional[str] = None
    password_configured: bool = False
    notes: Optional[str] = None


class ProjectEnvironment(BaseModel):
    project_id: str                # NEW — project this environment belongs to
    env_id: Optional[str] = None                    # ENV001
    env_type: str = "qa"

    base_url: str
    api_base_url: Optional[str] = None

    auth_type: Literal["none", "basic", "bearer"] = "none"
    auth_token: Optional[str] = Field(default=None, repr=False)
    auth_token_configured: bool = False
    clear_auth_token: bool = False
    revision: Optional[int] = Field(default=None, ge=0)

    credentials: List[EnvironmentCredentials] = Field(default_factory=list)

    default_browser: Literal["chromium", "firefox", "webkit"] = "chromium"
    default_headed: bool = False
    default_timeout_ms: int = 10000

    variables: Dict[str, Any] = Field(default_factory=dict)



class ProjectEnvironmentResponse(ProjectEnvironment):
    id: str
