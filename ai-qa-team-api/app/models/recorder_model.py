from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


class RecordedStep(BaseModel):
    """
    One recorded UI step from the front-end recorder.
    This is intentionally generic and future-proof.
    """
    order: int = Field(..., description="1-based order of the step in the recording")
    action: str = Field(..., description="Human readable action, e.g. 'Click Login button'")
    selector: Optional[str] = Field(
        None,
        description="CSS/XPath selector if available (optional for MVP)",
    )
    input_value: Optional[str] = Field(
        None,
        description="Input text/value if this was a typing action",
    )
    url: Optional[str] = Field(
        None,
        description="URL at the time of this step (optional)",
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw JS event, DOM metadata, etc. for future use",
    )


class RecordingCreate(BaseModel):
    """
    Payload from the frontend when user clicks `Save Recording`
    for a given Story.
    """
    story_id: str
    project_id: Optional[str] = None  # can be auto-derived from story on backend
    steps: List[RecordedStep]
    notes: Optional[str] = None
    agent_name: Optional[str] = Field(
        None,
        description="User-facing name of the Recorder Agent (per-project)",
    )

    class Config:
        populate_by_name = True
        from_attributes = True


class RecordingResponse(BaseModel):
    """
    What we return to the frontend when listing/fetching recordings.
    """
    id: str
    recording_id: str  # e.g. REC001
    story_id: str
    project_id: Optional[str] = None
    steps: List[RecordedStep]
    notes: Optional[str] = None
    agent_name: Optional[str] = None
    created_by: str
    created_at: str

    class Config:
        populate_by_name = True
        from_attributes = True
