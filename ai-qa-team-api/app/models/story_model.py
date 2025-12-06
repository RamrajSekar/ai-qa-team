from pydantic import BaseModel
from typing import Optional, List

class StoryCreate(BaseModel):
    project_id: str
    title: str
    description: str
    acceptance_criteria: Optional[str] = None
    out_of_scope: Optional[str] = None
    status: str = "pending"
    tags: Optional[List[str]] = []
    scenarios: List[str] = []

    class Config:
        populate_by_name = True
        from_attributes = True

class StoryResponse(BaseModel):
    project_id: str
    story_id: str
    title: str
    description: Optional[str]
    acceptance_criteria: Optional[str] = None
    out_of_scope: Optional[str] = None
    tags: Optional[List[str]] = []
    status: str
    scenarios: List[str] = []
    created_at: str
    created_by: str

    class Config:
        populate_by_name = True
        from_attributes = True

class StoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    out_of_scope: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    scenarios: Optional[List[str]] = None

    class Config:
        populate_by_name = True
