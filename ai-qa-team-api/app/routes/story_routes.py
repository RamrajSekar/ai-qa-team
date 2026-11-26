from fastapi import APIRouter, HTTPException, Depends, status
from app.db.connection import db
from app.models.story_model import StoryCreate, StoryResponse, StoryUpdate
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required
from app.services.subscription_services import get_subscription, increment_usage, decrement_usage
from app.services.story_service import get_next_sequence
from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from app.utils.project_authorization import require_project_member


router = APIRouter(prefix="/stories", tags=["Stories"])

@router.post("", response_model=StoryResponse, include_in_schema=False)
@router.post("/", response_model=StoryResponse)
async def create_story(
    story: StoryCreate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("stories"))
):
    try:
        user_email = current_user["email"]
        # 0️⃣ Validate the incoming project_id (business ID, not ObjectId)
        project,_ = await require_project_member(story.project_id,current_user)

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
            "acceptance_criteria": story.acceptance_criteria,
            "out_of_scope": story.out_of_scope,
            "status": story.status,
            "tags": story.tags or [],
            "scenarios": [],
            "created_by": current_user["email"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        from app.services.account_billing import billing_account
        from app.services.resource_quota import ResourceQuota
        billing = await billing_account(db, current_user)
        if billing and billing["subscription"].get("entitlement_version") == 2:
            saved = await ResourceQuota(db).create_account_resource(current_user, "stories", story_data)
            story_data["id"] = str(saved["_id"])
        else:
            result = await db["stories"].insert_one(story_data)
            story_data["id"] = str(result.inserted_id)
            await increment_usage(user_email, "stories_used")

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
@router.get("", response_model=list[StoryResponse], include_in_schema=False)
@router.get("/", response_model=list[StoryResponse])
async def list_stories(
    project_id: str,
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user)
):
    """Fetch all stories for a specific project."""
    user_id = current_user.get("email") or current_user.get("_id")

    await require_project_member(project_id,current_user)
    query = {"project_id": project_id}
    cursor = db["stories"].find(query).skip(skip).limit(limit)
    stories = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        doc.setdefault("tags", [])
        doc.setdefault("scenarios", [])
        stories.append(StoryResponse(**doc))
    return stories


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: str,
    project_id: str,                         
    current_user=Depends(get_current_user)
):
    try:
        user_email = current_user["email"]
        await require_project_member(project_id,current_user)

        story = await db["stories"].find_one({
            "story_id": story_id,
            "project_id": project_id, 
        })

        if not story:
            raise HTTPException(404, "Story not found or access denied.")

        story["id"] = str(story["_id"])
        story.pop("_id", None)

        return StoryResponse(**story)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch story: {str(e)}")


@router.patch("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: str,
    project_id: str, 
    payload: StoryUpdate,
    current_user=Depends(get_current_user)
):
    """
    Update a story using its sequential story_id (e.g., S001).
    Ensures ownership.
    """
    try:
        # user_id = current_user.get("_id") or current_user.get("id") or current_user.get("email")
        user_email = current_user["email"]
        await require_project_member(project_id,current_user)

        # Find story by sequential ID
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        result = await db["stories"].update_one(
            {
                "story_id": story_id,
                "project_id": project_id,
            },
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(404, "Story not found or access denied")

        updated = await db["stories"].find_one(
            {
                "story_id": story_id,
                "project_id": project_id,
            }
        )

        updated["id"] = str(updated["_id"])
        updated.pop("_id", None)

        return StoryResponse(**updated)
    except HTTPException:raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update story.") from None

    
@router.delete("/{story_id}")
async def delete_story(
    story_id: str,
    project_id: str,
    current_user=Depends(get_current_user)
):
    user_email = current_user["email"]
    await require_project_member(project_id,current_user)
    existing=await db["stories"].find_one({"story_id":story_id,"project_id":project_id})

    deleted = await db["stories"].delete_one({
        "story_id": story_id,
        "project_id": project_id,
    })

    if deleted.deleted_count == 0:
        raise HTTPException(404, "Story not found or access denied.")

    # NEW: decrement story usage
    await decrement_usage((existing or {}).get("created_by",user_email), "stories_used")

    return {"message": "Story deleted"}
