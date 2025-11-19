from fastapi import APIRouter, HTTPException, Depends, status
from app.db.connection import db
from app.models.story_model import StoryCreate, StoryResponse, StoryUpdate
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required
from app.services.story_service import get_next_sequence
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
    try:
        # 0️⃣ Validate the incoming project_id (business ID, not ObjectId)
        project = await db["projects"].find_one({
            "project_id": story.project_id,
            "created_by": current_user["email"]
        })

        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found or access denied."
            )

        # 1️⃣ Generate sequential ID for story (S001, S002)
        new_story_id = await get_next_sequence("story_id", "S")

        # 2️⃣ Build payload
        story_data = {
            "story_id": new_story_id,
            "project_id": story.project_id,                    # PR001 (Business ID)
            "project_ref": str(project["_id"]),               # Actual ObjectId (string)
            "title": story.title,
            "description": story.description,
            "status": story.status,
            "tags": story.tags or [],
            "scenarios": [],
            "created_by": current_user["email"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # 3️⃣ Insert into Mongo
        result = await db["stories"].insert_one(story_data)
        story_data["id"] = str(result.inserted_id)

        return StoryResponse(**story_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to create story: {str(e)}"
        )


# @router.get("/",response_model=List[StoryResponse])
# async def get_stories(skip: int = 0, limit: int = 20,current_user=Depends(get_current_user)):
#     """Fetch all stories created by the logged-in user."""
@router.get("/", response_model=list[StoryResponse])
async def list_stories(
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user)
):
    """Fetch all stories created by the logged-in user."""
    user_id = current_user.get("_id") or current_user.get("email")

    cursor = db["stories"].find({"created_by": user_id}).skip(skip).limit(limit)

    stories = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)

        doc.setdefault("tags", [])
        doc.setdefault("story_id", None)  # ← Prevent validation error

        stories.append(StoryResponse(**doc))

    return stories

@router.get("/{story_id}", response_model=StoryResponse)
async def get_story_by_id(story_id: str, current_user=Depends(get_current_user)):
    """
    Fetch a story using its sequential story_id (e.g., S001).
    Ensures the story belongs to the logged-in user.
    """
    try:
        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")

        # Find story by sequential story_id
        story = await db["stories"].find_one({
            "story_id": story_id,
            "created_by": user_id
        })

        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or access denied."
            )

        # Convert Mongo _id → string id
        story["id"] = str(story["_id"])
        story.pop("_id", None)
        story.setdefault("tags", [])
        story.setdefault("scenarios", [])

        return StoryResponse(**story)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch story: {str(e)}")


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: str,
    story_update: StoryUpdate,
    current_user=Depends(get_current_user)
):
    """
    Update a story using its sequential story_id (e.g., S001).
    Ensures ownership.
    """
    try:
        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")

        # Find story by sequential ID
        existing = await db["stories"].find_one({
            "story_id": story_id,
            "created_by": user_id
        })

        if not existing:
            raise HTTPException(status_code=404, detail="Story not found or access denied.")

        update_data = {
            k: v for k, v in story_update.model_dump().items()
            if v is not None
        }

        await db["stories"].update_one(
            {"story_id": story_id},
            {"$set": update_data}
        )

        updated = await db["stories"].find_one({"story_id": story_id})
        updated["id"] = str(updated["_id"])
        updated.pop("_id", None)

        updated.setdefault("tags", [])
        updated.setdefault("scenarios", [])

        return StoryResponse(**updated)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update story: {str(e)}")

    
@router.delete("/{story_id}")
async def delete_story(story_id: str, current_user=Depends(get_current_user)):
    """
    Delete a story using its sequential story_id (e.g., S001).
    Ensures ownership.
    """
    try:
        user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")

        result = await db["stories"].delete_one({
            "story_id": story_id,
            "created_by": user_id
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Story not found or access denied.")

        return {"message": "Story deleted successfully."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete story: {str(e)}")
