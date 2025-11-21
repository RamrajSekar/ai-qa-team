from app.db.connection import db
from fastapi import HTTPException
from app.models.environment_model import ProjectEnvironment


async def create_environment(env: ProjectEnvironment, current_user):
    env_dict = env.model_dump()
    env_dict["created_by"] = current_user["email"]

    result = await db["environments"].insert_one(env_dict)
    env_dict["id"] = str(result.inserted_id)
    return env_dict


async def list_environments(project_id: str | None, current_user):
    query = {"created_by": current_user["email"]}

    if project_id:
        query["project_id"] = project_id

    cursor = db["environments"].find(query)
    return [ {**doc, "id": str(doc["_id"])} for doc in await cursor.to_list(100) ]


async def get_environment(env_id: str, current_user):
    doc = await db["environments"].find_one({
        "env_id": env_id,
        "created_by": current_user["email"]
    })

    if not doc:
        raise HTTPException(404, "Environment not found")

    doc["id"] = str(doc["_id"])
    return doc


async def update_environment(env_id: str, env: ProjectEnvironment, current_user):
    updated = await db["environments"].update_one(
        {"env_id": env_id, "created_by": current_user["email"]},
        {"$set": env.model_dump()}
    )

    if updated.matched_count == 0:
        raise HTTPException(404, "Environment not found")

    return await get_environment(env_id, current_user)


async def delete_environment(env_id: str, current_user):
    deleted = await db["environments"].delete_one({
        "env_id": env_id,
        "created_by": current_user["email"]
    })

    if deleted.deleted_count == 0:
        raise HTTPException(404, "Environment not found")

    return {"message": "Environment deleted"}
