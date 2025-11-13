from fastapi import APIRouter, HTTPException, Depends, status
from app.db.connection import db
from app.models.story_model import StoryCreate, StoryResponse
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required
from datetime import datetime, timezone
from typing import List
from bson import ObjectId


router = APIRouter(prefix="/stories", tags=["Stories"])

@router.post("/", response_model=StoryResponse)
async def create_story(
     story: StoryCreate,
     current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("stories"))
    ):
    # story creation logic here
    try:
        story_data = story.model_dump()
        story_data["created_by"] = current_user.get("email")
        story_data["created_at"] = datetime.now(timezone.utc).isoformat()

        result = await db["stories"].insert_one(story_data)
        story_data["id"] = str(result.inserted_id)
        story_data.setdefault("tags", []) 
        return StoryResponse(**story_data)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create story: {str(e)}")

@router.get("/",response_model=List[StoryResponse])
async def get_stories(skip: int = 0, limit: int = 20,current_user=Depends(get_current_user)):
    """Fetch all stories created by the logged-in user."""
    user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")
    stories_cursor = db["stories"].find({"created_by": user_id}).skip(skip).limit(limit)
    stories = await stories_cursor.to_list(length=None)

    # handle no results
    if not stories:
        raise HTTPException(status_code=404, detail="No stories found.")
    
    # convert _id -> id string for response
    for s in stories:
        s["id"] = str(s["_id"])
        s.pop("_id", None)
        s.setdefault("tags", [])  # ensure optional field

    return [StoryResponse(**s) for s in stories]

@router.get("/{story_id}", response_model=StoryResponse)
async def get_story_by_id(story_id: str, current_user=Depends(get_current_user)):
    """
    Fetch a single story by its ID.
    Ensures the story belongs to the logged-in user.
    """
    try:
        # Convert to ObjectId safely
        if not ObjectId.is_valid(story_id):
            raise HTTPException(status_code=400, detail="Invalid story ID format.")

        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")

        # Query story and enforce ownership
        story = await db["stories"].find_one({"_id": ObjectId(story_id), "created_by": user_id})

        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or access denied."
            )

        # Convert and prepare response
        story["id"] = str(story["_id"])
        story.pop("_id", None)
        story.setdefault("tags", [])

        return StoryResponse(**story)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch story: {str(e)}")


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(story_id: str, story_update: StoryCreate, current_user=Depends(get_current_user)):
    """
    Update an existing story if owned by the logged-in user.
    """
    try:
        if not ObjectId.is_valid(story_id):
            raise HTTPException(status_code=400, detail="Invalid story ID format.")

        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")

        # Check ownership
        existing = await db["stories"].find_one({"_id": ObjectId(story_id), "created_by": user_id})
        if not existing:
            raise HTTPException(status_code=404, detail="Story not found or access denied.")

        update_data = {k: v for k, v in story_update.model_dump().items() if v is not None}
        await db["stories"].update_one({"_id": ObjectId(story_id)}, {"$set": update_data})

        # Fetch the updated story
        updated_story = await db["stories"].find_one({"_id": ObjectId(story_id)})
        updated_story["id"] = str(updated_story["_id"])
        updated_story.pop("_id", None)
        updated_story.setdefault("tags", [])

        return StoryResponse(**updated_story)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update story: {str(e)}")
    
@router.delete("/{story_id}")
async def delete_story(story_id: str, current_user=Depends(get_current_user)):
    """
    Delete a story owned by the logged-in user.
    """
    try:
        if not ObjectId.is_valid(story_id):
            raise HTTPException(status_code=400, detail="Invalid story ID format.")

        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")

        result = await db["stories"].delete_one({"_id": ObjectId(story_id), "created_by": user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Story not found or access denied.")

        return {"message": "Story deleted successfully."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete story: {str(e)}")
