from app.db.connection import db
from fastapi import HTTPException
from app.models.environment_model import (
    ProjectEnvironment,
    ProjectEnvironmentResponse,
)
from app.services.story_service import get_next_sequence
from app.utils.project_authorization import require_project_admin, require_project_member

# -------------------------------------------------------
# CREATE ENVIRONMENT
# -------------------------------------------------------
async def create_environment(env: ProjectEnvironment, current_user):
    await require_project_admin(env.project_id, current_user)
    # Generate sequential environment ID like ENV001
    new_env_id = await get_next_sequence("env_id", "ENV")

    # Convert incoming model → dictionary but EXCLUDE env_id
    env_dict = env.model_dump(exclude={"env_id"})

    # Inject system-generated fields
    env_dict["env_id"] = new_env_id
    env_dict["created_by"] = current_user["email"]

    # Insert into DB
    result = await db["environments"].insert_one(env_dict)

    # Add public-facing ID
    env_dict["id"] = str(result.inserted_id)

    # --- Update Onboarding State ---
    await db["users"].update_one(
        {"email": current_user["email"]},
        {
            "$set": {
                "onboarding.context.environment_id": new_env_id,
                "onboarding.steps.environment": True,
                "onboarding.current_step": 3
            }
        }
    )

    # Return response model
    return ProjectEnvironmentResponse(**env_dict)

# -------------------------------------------------------
# LIST ENVIRONMENTS
# -------------------------------------------------------
# async def list_environments(project_id: str | None, current_user):
#     query = {"created_by": current_user["email"]}

#     if project_id:
#         query["project_id"] = project_id

#     cursor = db["environments"].find(query)
#     docs = await cursor.to_list(100)

#     return [
#         ProjectEnvironmentResponse(
#             **{**doc, "id": str(doc["_id"])}
#         )
#         for doc in docs
#     ]

async def list_environments(project_id: str | None, current_user):
    if project_id:
        await require_project_member(project_id, current_user)
        query = {"project_id": project_id}
    else:
        memberships = await db["project_memberships"].find({
            "email": current_user["email"].lower(), "status": "ACTIVE",
        }).to_list(500)
        query = {"project_id": {"$in": [item["project_id"] for item in memberships]}}
    cursor = db["environments"].find(query)
    results = await cursor.to_list(100)
    parsed = [{**doc, "id": str(doc["_id"])} for doc in results]
    return parsed

# -------------------------------------------------------
# GET SINGLE ENVIRONMENT
# -------------------------------------------------------
async def get_environment(env_id: str, current_user):
    doc = await db["environments"].find_one({"env_id": env_id})

    if not doc:
        raise HTTPException(404, "Environment not found")
    await require_project_member(doc["project_id"], current_user)

    doc["id"] = str(doc["_id"])
    return ProjectEnvironmentResponse(**doc)

# -------------------------------------------------------
# UPDATE ENVIRONMENT
# -------------------------------------------------------
async def update_environment(env_id: str, env: ProjectEnvironment, current_user):
    existing = await db["environments"].find_one({"env_id": env_id})
    if not existing:
        raise HTTPException(404, "Environment not found")
    await require_project_admin(existing["project_id"], current_user)
    # Do NOT allow env_id or project_id to be overwritten
    update_data = env.model_dump()
    update_data.pop("env_id", None)
    update_data.pop("project_id", None)

    updated = await db["environments"].update_one(
        {"env_id": env_id},
        {"$set": update_data}
    )

    if updated.matched_count == 0:
        raise HTTPException(404, "Environment not found")

    return await get_environment(env_id, current_user)

# -------------------------------------------------------
# DELETE ENVIRONMENT
# -------------------------------------------------------
async def delete_environment(env_id: str, current_user):
    existing = await db["environments"].find_one({"env_id": env_id})
    if not existing:
        raise HTTPException(404, "Environment not found")
    await require_project_admin(existing["project_id"], current_user)
    deleted = await db["environments"].delete_one({"env_id": env_id})

    if deleted.deleted_count == 0:
        raise HTTPException(404, "Environment not found")

    return {"message": "Environment deleted"}
