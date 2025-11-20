from typing import List, Optional
from datetime import datetime, timezone

from fastapi import HTTPException, status
from bson import ObjectId

from app.db.connection import db
from app.models.recorder_model import RecordingCreate, RecordingResponse, RecordedStep
from app.services.story_service import get_next_sequence


def _to_response(doc: dict) -> RecordingResponse:
    """
    Convert MongoDB doc → RecordingResponse.
    """
    return RecordingResponse(
        id=str(doc["_id"]),
        recording_id=doc["recording_id"],
        story_id=doc["story_id"],
        project_id=doc.get("project_id"),
        steps=[RecordedStep(**s) for s in doc.get("steps", [])],
        notes=doc.get("notes"),
        agent_name=doc.get("agent_name"),
        created_by=doc["created_by"],
        created_at=doc["created_at"],
    )


async def create_recording(payload: RecordingCreate, user_email: str) -> RecordingResponse:
    # 1. Ensure story belongs to this user
    story = await db["stories"].find_one(
        {"story_id": payload.story_id, "created_by": user_email}
    )
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found or access denied.",
        )

    # 2. Determine project_id (prefer payload but fallback to story)
    project_id = payload.project_id or story.get("project_id")

    # 3. Fetch project to get recorder agent identity
    project = await db["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found for this story.",
        )

    agent_name = project.get("agent_identities", {}).get("recorder", "Recorder Agent")

    # 4. Generate RECxxx sequence
    recording_id = await get_next_sequence("recording_id", "REC")

    doc = {
        "recording_id": recording_id,
        "story_id": payload.story_id,
        "project_id": project_id,
        "steps": [step.model_dump() for step in payload.steps],
        "notes": payload.notes,
        "agent_name": agent_name,
        "created_by": user_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await db["recordings"].insert_one(doc)
    doc["_id"] = result.inserted_id

    return _to_response(doc)


async def list_recordings_for_story(story_id: str, user_email: str) -> List[RecordingResponse]:
    """
    List all recordings for a story for this user.
    """
    cursor = db["recordings"].find(
        {"story_id": story_id, "created_by": user_email}
    ).sort("created_at", 1)

    results: List[RecordingResponse] = []
    async for doc in cursor:
        results.append(_to_response(doc))
    return results


async def get_recording_by_id(recording_id: str, user_email: str) -> RecordingResponse:
    """
    Fetch a single recording by its RECxxx ID for this user.
    """
    doc = await db["recordings"].find_one(
        {"recording_id": recording_id, "created_by": user_email}
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found or access denied.",
        )
    return _to_response(doc)


async def delete_recording(recording_id: str, user_email: str) -> None:
    """
    Delete a recording by recording_id for this user.
    """
    result = await db["recordings"].delete_one(
        {"recording_id": recording_id, "created_by": user_email}
    )
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found or access denied.",
        )
