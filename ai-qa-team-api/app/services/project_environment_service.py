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
    print("DEBUG: list_environments called")
    print("DEBUG: project_id =", project_id)
    print("DEBUG: current_user =", current_user["email"])

    query = {"created_by": current_user["email"]}

    if project_id:
        query["project_id"] = project_id

    print("DEBUG: MongoDB Query =", query)

    cursor = db["environments"].find(query)
    results = await cursor.to_list(100)

    print("DEBUG: RAW RESULTS FROM DB =", results)

    parsed = [{**doc, "id": str(doc["_id"])} for doc in results]

    print("DEBUG: PARSED ENVIRONMENTS RETURNED =", parsed)

    return parsed

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
