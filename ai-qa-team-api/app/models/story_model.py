from pydantic import BaseModel
from typing import Optional, List

class Story(BaseModel):
    id: Optional[str]
    project_id: str
    title: str
    description: str
    status: str = "pending"
    scenarios: List[str] = []
