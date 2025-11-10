from fastapi import APIRouter, HTTPException, Depends
from app.db.connection import db
from app.models.story_model import Story
from app.utils.auth_dependency import get_current_user,role_required

router = APIRouter(prefix="/stories", tags=["Stories"])

@router.post("/")
async def create_story(story: Story,current_user=Depends(role_required("admin"))):
    result = await db["stories"].insert_one(story.model_dump())
    return {"id": str(result.inserted_id), "message": f"Story added successfully by {current_user['email']}"}

@router.get("/")
async def get_stories(current_user=Depends(get_current_user)):
    return {"message": f"Stories visible to {current_user['email']}"}