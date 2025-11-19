from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

class TestStep(BaseModel):
    step_id: str
    action: str
    locator: Optional[str] = None
    value: Optional[str] = None
    expected: str
    category: str

class TestCaseCreate(BaseModel):
    # existing fields...
    testcase_id: Optional[str] = None
    story_id: Optional[str] = None
    scenario_id: Optional[str] = None
    project_id: str

    title: str
    description: Optional[str] = None

    # steps is already a List[TestStep] or similar
    steps: List[TestStep]

    # ✅ NEW: attach reusable test data
    data_set_id: Optional[str] = None
    data_overrides: Dict[str, Any] = Field(default_factory=dict)

class TestCaseResponse(BaseModel):
    testcase_id: str
    scenario_id: str
    project_id: str
    title: str
    description: Optional[str]
    steps: List[TestStep]
    status: str
    code: str
    created_by: str
    created_at: str
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        populate_by_name = True
        from_attributes = True
