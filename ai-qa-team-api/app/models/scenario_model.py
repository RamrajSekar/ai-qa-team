from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

class StepModel(BaseModel):
    step_id: str
    category: str = "UI"  # UI / API / Navigation / Validation / Assertion
    action: str
    expected: str | None = None

class ScenarioCreate(BaseModel):
    story_id: str
    title: str
    description: Optional[str] = None
    steps: List[StepModel] = []
    generated_by_agent: Optional[str] = None
    complexity: Optional[str] = None
class ScenarioUpdate(BaseModel):
    scenario_id: str
    story_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[dict]] = None
    status: Optional[str] = None
    complexity: Optional[str] = None


class ScenarioResponse(BaseModel):
    scenario_id: str
    story_id: str
    project_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    steps: List[StepModel]
    status: str = "pending"
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    generated_by_agent: Optional[str] = None
    complexity: Optional[str] = None



class ScenarioDB(BaseModel):
    story_id: str
    title: str
    description: Optional[str]
    steps: List[dict]
    status: str = "pending"
    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generated_by_agent: Optional[str] = None
    complexity: Optional[str] = None


class ScenarioGenerationSummary(BaseModel):
    message: str
    remaining_ai_generations: Optional[int] | str
    remaining_scenario_slots: Optional[int] | str
    plan: str


class ScenarioGenerationResponse(BaseModel):
    scenarios: List[ScenarioResponse]
    summary: ScenarioGenerationSummary