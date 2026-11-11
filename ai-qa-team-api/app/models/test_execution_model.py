from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal, Dict, Any


class StepResult(BaseModel):
    step_id: str
    status: Literal['passed', 'failed', 'skipped']
    message: Optional[str] = None
    duration_ms: Optional[int] = None
    screenshot_path: Optional[str] = None
    error_stack: Optional[str] = None


# ============================================================
#   CLEAN — FINAL EXECUTION MODEL
# ============================================================
class TestExecution(BaseModel):
    execution_id: str
    project_id: str

    story_id: Optional[str] = None
    scenario_id: Optional[str] = None
    testcase_id: str

    status: Literal["queued", "running", "passed", "failed", "error"] = "queued"
    complexity: Optional[str] = None  # basic | medium | advanced | None (legacy)

    env_type: str                                 # "qa", "dev", "staging", ...
    env_id: Optional[str] = None                  # ENV001
    role: Optional[str] = None                    # selected role

    environment_doc: Dict[str, Any] = Field(default_factory=dict)  
    credentials: Optional[Dict[str, Any]] = None

    base_url: Optional[str] = None
    api_base_url: Optional[str] = None
    env_variables: Dict[str, Any] = Field(default_factory=dict)

    auth_type: Optional[str] = None
    auth_token: Optional[str] = None

    # --------------------------------------------------------
    # Browser + Execution
    # --------------------------------------------------------
    browser: Optional[str] = None
    headed: bool = False
    dataset: Optional[dict | str] = None

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    triggered_by: str
    runner_type: Literal["playwright-local", "playwright-cloud", "manual"]

    step_results: List[StepResult] = Field(default_factory=list)
    logs: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# ============================================================
# RESPONSE MODEL
# ============================================================
class TestExecutionResponse(BaseModel):
    id: str
    execution_id: str
    project_id: str

    story_id: Optional[str] = None
    scenario_id: Optional[str] = None
    testcase_id: str
    complexity: Optional[str] = None
    status: str

    # Environment info
    env_type: Optional[str] = None
    env_id: Optional[str] = None
    role: Optional[str] = None

    environment_doc: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Any]] = None

    base_url: Optional[str] = None
    api_base_url: Optional[str] = None
    env_variables: Dict[str, Any] = Field(default_factory=dict)

    auth_type: Optional[str] = None
    auth_token: Optional[str] = None

    # Browser + dataset
    browser: Optional[str] = None
    headed: bool
    dataset: Optional[dict | str] = None

    # Time
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    triggered_by: str
    runner_type: str

    step_results: List[StepResult] = Field(default_factory=list)
    logs: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        from_attributes = True


# ============================================================
# BATCH EXECUTION REQUEST
# ============================================================
class BatchExecuteRequest(BaseModel):
    testcase_ids: List[str]
    browser: Optional[str] = None
    dataset: Optional[dict | str] = None
    headed: bool = False
    parallel: bool = False
