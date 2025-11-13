from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone

class TestStep(BaseModel):
    action: str
    locator: Optional[str] = None
    value: Optional[str] = None

class TestCaseCreate(BaseModel):
    scenario_id: str
    title: str
    steps: List[TestStep]

class TestCaseResponse(BaseModel):
    testcase_id: str
    scenario_id: str
    title: str
    steps: List[TestStep]
    status: str
    created_by: str
    created_at: str
    updated_at: str
    defect_id: Optional[str] = None
