from datetime import datetime
from app.models.story_model import StoryResponse
from app.db.connection import db
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


async def get_stories_by_Id(user_identifier: str):
    logger.info(f"Checking Story for user: {user_identifier}")
    user = await db["users"].find_one(
        {"$or": [{"_id": user_identifier}, {"id": user_identifier}, {"email": user_identifier}]},
    )
    if not user:
        logger.warning(f"User not found for {user_identifier}")
        return None

    stories = user.get("StoryResponse")
    if not stories:
        logger.warning(f"No stories created for {user_identifier}")
        return None

    logger.info(f"Stories fetched for {user_identifier}: {sub.get('plan', 'unknown')}")
    return stories