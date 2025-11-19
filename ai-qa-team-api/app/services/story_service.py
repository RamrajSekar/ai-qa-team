from datetime import datetime
from app.models.story_model import StoryResponse
from app.db.connection import db
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


async def get_next_sequence(key: str, prefix: str, digits: int = 3) -> str:
    """
    Returns the next auto-increment ID for a resource.
    Example:
        key="project_id", prefix="PRJ" → PRJ001
        key="story_id", prefix="S" → S001
        key="scenario_id", prefix="SC" → SC001
        key="testcase_id", prefix="TC" → TC001
    """
    result = await db["counters"].find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )

    seq = result["seq"]
    return f"{prefix}{seq:0{digits}d}"