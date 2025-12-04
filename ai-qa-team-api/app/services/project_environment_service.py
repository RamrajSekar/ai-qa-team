from app.db.connection import db
from fastapi import HTTPException
from app.models.environment_model import (
    ProjectEnvironment,
    ProjectEnvironmentResponse,
)
from app.services.story_service import get_next_sequence

# -------------------------------------------------------
# CREATE ENVIRONMENT
# -------------------------------------------------------
async def create_environment(env: ProjectEnvironment, current_user):
    # Auto-generate environment ID
    new_env_id = await get_next_sequence("env_id", "ENV")

    env_dict = env.model_dump()
    env_dict["env_id"] = new_env_id
    env_dict["created_by"] = current_user["email"]

    result = await db["environments"].insert_one(env_dict)
    env_dict["id"] = str(result.inserted_id)

    return ProjectEnvironmentResponse(**env_dict)

# -------------------------------------------------------
# LIST ENVIRONMENTS
# -------------------------------------------------------
async def list_environments(project_id: str | None, current_user):
    query = {"created_by": current_user["email"]}

    if project_id:
        query["project_id"] = project_id

    cursor = db["environments"].find(query)
    docs = await cursor.to_list(100)

    return [
        ProjectEnvironmentResponse(
            **{**doc, "id": str(doc["_id"])}
        )
        for doc in docs
    ]

# -------------------------------------------------------
# GET SINGLE ENVIRONMENT
# -------------------------------------------------------
async def get_environment(env_id: str, current_user):
    doc = await db["environments"].find_one({
        "env_id": env_id,
        "created_by": current_user["email"]
    })

    if not doc:
        raise HTTPException(404, "Environment not found")

    doc["id"] = str(doc["_id"])
    return ProjectEnvironmentResponse(**doc)

# -------------------------------------------------------
# UPDATE ENVIRONMENT
# -------------------------------------------------------
async def update_environment(env_id: str, env: ProjectEnvironment, current_user):
    # Do NOT allow env_id or project_id to be overwritten
    update_data = env.model_dump()
    update_data.pop("env_id", None)
    update_data.pop("project_id", None)

    updated = await db["environments"].update_one(
        {"env_id": env_id, "created_by": current_user["email"]},
        {"$set": update_data}
    )

    if updated.matched_count == 0:
        raise HTTPException(404, "Environment not found")

    return await get_environment(env_id, current_user)

# -------------------------------------------------------
# DELETE ENVIRONMENT
# -------------------------------------------------------
async def delete_environment(env_id: str, current_user):
    deleted = await db["environments"].delete_one({
        "env_id": env_id,
        "created_by": current_user["email"]
    })

    if deleted.deleted_count == 0:
        raise HTTPException(404, "Environment not found")

    return {"message": "Environment deleted"}
