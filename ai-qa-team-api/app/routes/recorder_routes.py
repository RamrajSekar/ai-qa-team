from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.db.connection import db
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required
from app.models.recorder_model import RecordingCreate, RecordingResponse
from app.services.recorder_service import (
    create_recording,
    list_recordings_for_story,
    get_recording_by_id,
    delete_recording,
)

router = APIRouter(prefix="/recorder", tags=["Recorder"])


# ------------------------------------------------------
# 1) SAVE A RECORDING
# ------------------------------------------------------
@router.post("/", response_model=RecordingResponse)
async def save_recording(
    payload: RecordingCreate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("ai_generation")),
):
    """
    Save a recording captured via the JS Snippet Recorder.
    Later this recording can be used for AI-powered scenario generation.
    """
    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(401, "Missing user email from token")

    return await create_recording(payload, user_email)


# ------------------------------------------------------
# 2) FETCH RECORDINGS FOR A STORY
# ------------------------------------------------------
@router.get("/by-story/{story_id}", response_model=List[RecordingResponse])
async def get_recording_for_story(story_id: str, user_email: str):
    """
    Returns the *latest* recording for a story, or None.
    """
    doc = await db["recordings"].find_one(
        {"story_id": story_id, "created_by": user_email},
        sort=[("created_at", -1)]
    )

    return doc  # dict or None



# ------------------------------------------------------
# 3) FETCH SINGLE RECORDING
# ------------------------------------------------------
@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str,
    current_user=Depends(get_current_user),
):
    user_email = current_user.get("email")
    return await get_recording_by_id(recording_id, user_email)


# ------------------------------------------------------
# 4) DELETE A RECORDING
# ------------------------------------------------------
@router.delete("/{recording_id}")
async def remove_recording(
    recording_id: str,
    current_user=Depends(get_current_user),
):
    user_email = current_user.get("email")
    await delete_recording(recording_id, user_email)
    return {"message": "Recording deleted successfully."}


# ------------------------------------------------------
# 5) SPECIAL: FETCH RECORDING TO USE IN AI SCENARIO GENERATION
# ------------------------------------------------------
@router.get("/story/{story_id}/latest", response_model=RecordingResponse)
async def get_latest_recording_for_story(
    story_id: str,
    current_user=Depends(get_current_user),
):
    """
    Returns the most recent recording for a story.
    Useful for UI: “Use Latest Recording to Generate Scenarios”
    """
    user_email = current_user.get("email")
    rec = await get_latest_recording_for_story(story_id, user_email)

    if not rec:
        raise HTTPException(404, "No recordings found for this story")

    return rec
