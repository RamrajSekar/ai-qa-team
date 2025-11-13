from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone


class ScenarioCreate(BaseModel):
    story_id: str
    title: str
    description: Optional[str] = None
    steps: List[dict] = []


class ScenarioUpdate(BaseModel):
    scenario_id: str
    story_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[dict]] = None
    status: Optional[str] = None


class ScenarioResponse(BaseModel):
    scenario_id: str
    story_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    steps: List[dict] = Field(default_factory=list)
    status: str = "pending"
    created_by: Optional[str] = None
    created_at: Optional[str] = None



class ScenarioDB(BaseModel):
    story_id: str
    title: str
    description: Optional[str]
    steps: List[dict]
    status: str = "pending"
    created_by: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
