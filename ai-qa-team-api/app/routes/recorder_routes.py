from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.utils.auth_dependency import get_current_user
from app.utils.subscription_dependency import subscription_required
from app.models.recorder_model import RecordingCreate, RecordingResponse
from app.services.recorder_service import (
    create_recording,
    list_recordings_for_story,
    get_recording_by_id,
    delete_recording,
    get_latest_recording_for_story
)

router = APIRouter(prefix="/recorder", tags=["Recorder"])

# 1) Save recording
@router.post("/", response_model=RecordingResponse)
async def save_recording(
    payload: RecordingCreate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("ai_generation")),
):
    return await create_recording(payload, current_user["email"])


@router.get("/by-project/{project_id}")
async def recordings_for_project(project_id: str, current_user=Depends(get_current_user)):
    user_email = current_user["email"]

    recs = await db["recordings"].find(
        {"project_id": project_id, "created_by": user_email}
    ).to_list(None)

    for r in recs:
        r["id"] = str(r["_id"])
        r.pop("_id", None)

    return recs

# 2) List all recordings for story
@router.get("/by-story/{story_id}", response_model=List[RecordingResponse])
async def recordings_for_story(
    story_id: str,
    current_user=Depends(get_current_user)
):
    return await list_recordings_for_story(story_id, current_user["email"])

# 3) Get one recording
@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: str,
    current_user=Depends(get_current_user)
):
    rec = await get_recording_by_id(recording_id, current_user["email"])
    if not rec:
        raise HTTPException(404, "Recording not found")
    return rec

# 4) Delete recording
@router.delete("/{recording_id}")
async def remove_recording(
    recording_id: str,
    current_user=Depends(get_current_user)
):
    await delete_recording(recording_id, current_user["email"])
    return {"message": "Recording deleted successfully"}

# 5) Fetch latest recording
@router.get("/story/{story_id}/latest", response_model=RecordingResponse)
async def latest_recording_route(
    story_id: str,
    current_user=Depends(get_current_user)
):
    rec = await get_latest_recording_for_story(story_id, current_user["email"])
    if not rec:
        raise HTTPException(404, "No recordings found")
    return rec
