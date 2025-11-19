from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, List, Literal, Dict, Any


class StepResult(BaseModel):
    step_id: str
    status: Literal['passed', 'failed', 'skipped']
    message: Optional[str] = None
    duration_ms: Optional[int] = None
    screenshot_path: Optional[str] = None
    error_stack: Optional[str] = None

class TestExecution(BaseModel):
    execution_id: str
    project_id: str
    story_id: Optional[str] = None
    scenario_id: Optional[str] = None
    testcase_id: str

    status: Literal["queued", "running", "passed", "failed", "error"] = "queued"

    environment: Optional[str] = None
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


class TestExecutionResponse(BaseModel):
    id: str
    execution_id: str
    project_id: str
    story_id: Optional[str] = None
    scenario_id: Optional[str] = None
    testcase_id: str

    status: str
    environment: Optional[str] = None
    browser: Optional[str] = None
    headed: bool
    dataset: Optional[dict | str] = None

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


class BatchExecuteRequest(BaseModel):
    testcase_ids: List[str]
    environment: Optional[str] = None
    browser: Optional[str] = None
    dataset: Optional[dict | str] = None  
    headed: bool = False
    parallel: bool = False  # reserved for future
