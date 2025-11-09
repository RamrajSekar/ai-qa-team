from fastapi import APIRouter, HTTPException
from app.db.connection import db
from app.models.story_model import Story

router = APIRouter(prefix="/stories", tags=["Stories"])

@router.post("/")
async def create_story(story: Story):
    result = await db["stories"].insert_one(story.dict())
    return {"id": str(result.inserted_id), "message": "Story added successfully"}
