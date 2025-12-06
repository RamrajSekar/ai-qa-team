from app.db.connection import db
# from app.services.story_service import get_story_by_business_id
from app.services.story_service import get_next_sequence
from app.models.recorder_model import RecordingCreate, RecordingResponse
from datetime import datetime, timezone
from bson import ObjectId

# ---------------------------------------------------------
# CREATE RECORDING
# ---------------------------------------------------------
async def create_recording(payload: RecordingCreate, user_email: str):

    # 1️⃣ Resolve project_id if frontend didn’t send it
    if not payload.project_id:
        story = await db["stories"].find_one({"story_id": payload.story_id})
        if not story:
            raise Exception("Story not found")
        payload.project_id = story.get("project_id")

    # 2️⃣ Generate recording_id (REC001)
    new_rec_id = await get_next_sequence("recording_id", "REC")

    # 3️⃣ Sort steps by order
    ordered_steps = sorted(payload.steps, key=lambda s: s.order)

    now_iso = datetime.now(timezone.utc).isoformat()

    doc = {
        "recording_id": new_rec_id,
        "story_id": payload.story_id,
        "project_id": payload.project_id,
        "steps": [step.model_dump() for step in ordered_steps],
        "notes": payload.notes,
        "agent_name": payload.agent_name,
        "created_by": user_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": payload.status or "completed",
        "is_editable": True,
        "updated_at": now_iso,
        "updated_by": user_email,
    }

    result = await db["recordings"].insert_one(doc)
    doc["id"] = str(result.inserted_id)

    return RecordingResponse(**doc)


# ---------------------------------------------------------
# LIST RECORDINGS FOR STORY
# ---------------------------------------------------------
# async def list_recordings_for_story(story_id: str, user_email: str):
#     cursor = db["recordings"].find(
#         {"story_id": story_id, "created_by": user_email},
#         sort=[("created_at", -1)]
#     )
#     output = []
#     async for doc in cursor:
#         doc["id"] = str(doc["_id"])
#         doc.pop("_id", None)
#         output.append(RecordingResponse(**doc))
#     print(f" From list_recordings_for_story: {output}")
#     return output

async def list_recordings_for_story(story_id: str, user_email: str):
    print("DEBUG list_recordings_for_story: story_id=", story_id)

    cursor = db["recordings"].find({
        "story_id": story_id,
        "created_by": user_email
    })

    results = await cursor.to_list(length=200)
    print("DEBUG recordings found:", results)

    safe = []
    for rec in results:
        try:
            rec["id"] = str(rec["_id"])
            rec.pop("_id", None)
            safe.append(RecordingResponse(**rec))
        except Exception as e:
            print("ERROR processing recording:", e, rec)

    return safe

# ---------------------------------------------------------
# SINGLE RECORDING
# ---------------------------------------------------------
async def get_recording_by_id(recording_id: str, user_email: str):
    doc = await db["recordings"].find_one(
        {"recording_id": recording_id, "created_by": user_email}
    )

    if not doc:
        return None

    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return RecordingResponse(**doc)


# ---------------------------------------------------------
# LATEST RECORDING FOR STORY
# ---------------------------------------------------------
async def get_latest_recording_for_story(story_id: str, user_email: str):
    doc = await db["recordings"].find_one(
        {"story_id": story_id, "created_by": user_email},
        sort=[("created_at", -1)]
    )
    if not doc:
        return None

    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return RecordingResponse(**doc)


# ---------------------------------------------------------
# DELETE RECORDING
# ---------------------------------------------------------
async def delete_recording(recording_id: str, user_email: str):
    result = await db["recordings"].delete_one(
        {"recording_id": recording_id, "created_by": user_email}
    )

    if result.deleted_count == 0:
        raise Exception("Recording not found or unauthorized")
