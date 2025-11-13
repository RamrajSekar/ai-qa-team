from pydantic import BaseModel
from typing import Optional, List

class StoryCreate(BaseModel):
    project_id: str
    title: str
    description: str
    status: str = "pending"
    tags: Optional[List[str]] = []
    scenarios: List[str] = []

    class Config:
        populate_by_name = True
        from_attributes = True

class StoryResponse(BaseModel):
    story_id: str
    title: str
    description: Optional[str]
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
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    scenarios: Optional[List[str]] = None

    class Config:
        populate_by_name = True
