from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class TestDataSet(BaseModel):
    id: Optional[str] = None      # Mongo _id as string
    data_id: str                  # TD001, TD002...
    project_id: str

    name: str
    description: Optional[str] = None

    # Arbitrary key/value pairs, e.g. {"qa_email": "qa@example.com"}
    data: Dict[str, Any] = Field(default_factory=dict)

    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
