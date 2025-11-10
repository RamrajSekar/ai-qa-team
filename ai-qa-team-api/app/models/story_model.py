from pydantic import BaseModel
from typing import Optional, List

class Story(BaseModel):
    id: Optional[str]
    project_id: str
    title: str
    description: str
    status: str = "pending"
    scenarios: List[str] = []

    class Config:
        populate_by_name = True
        from_attributes = True