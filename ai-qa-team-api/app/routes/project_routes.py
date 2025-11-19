from fastapi import APIRouter, Depends, HTTPException
from app.db.connection import db
from bson.objectid import ObjectId
from datetime import datetime, timezone
from app.models.project_model import AgentIdentities
from app.utils.auth_dependency import get_current_user
from app.services.story_service import get_next_sequence
from app.models.project_model import ProjectCreate, ProjectResponse, AgentIdentities
from app.utils.subscription_dependency import subscription_required

router = APIRouter(prefix="/projects", tags=["Projects"])


# -------------------------------------------------------------------
# 1. CREATE PROJECT
# -------------------------------------------------------------------
@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("projects"))
):
    new_project_id = await get_next_sequence("project_id", "PRJ")

    data = project.model_dump()
    data["project_id"] = new_project_id
    data["created_by"] = current_user["email"]
    data["created_at"] = datetime.now(timezone.utc).isoformat()

    # FIX: Convert AgentIdentities → dict
    if hasattr(project, "agent_identities"):
        data["agent_identities"] = project.agent_identities.model_dump()
    else:
        data["agent_identities"] = {}

    result = await db["projects"].insert_one(data)
    data["id"] = str(result.inserted_id)

    return ProjectResponse(**data)

# -------------------------------------------------------------------
# 2. LIST PROJECTS FOR USER
# -------------------------------------------------------------------
@router.get("/", response_model=list[ProjectResponse])
async def list_projects(current_user=Depends(get_current_user)):
    email = current_user.get("email")

    cursor = db["projects"].find({"created_by": email})
    projects = []

    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        projects.append(ProjectResponse(**doc))

    return projects


# -------------------------------------------------------------------
# 3. GET SINGLE PROJECT
# -------------------------------------------------------------------
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user=Depends(get_current_user)
):
    email = current_user.get("email")

    project = await db["projects"].find_one({"project_id": project_id, "created_by": email})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project["id"] = str(project["_id"])
    del project["_id"]

    return ProjectResponse(**project)


# -------------------------------------------------------------------
# 4. UPDATE PROJECT NAME
# -------------------------------------------------------------------
@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: dict,
    current_user=Depends(get_current_user)
):
    email = current_user.get("email")

    update_data = {k: v for k, v in data.items() if v is not None}

    result = await db["projects"].update_one(
        {"project_id": project_id, "created_by": email},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    updated = await db["projects"].find_one({"project_id": project_id})
    updated["id"] = str(updated["_id"])
    del updated["_id"]

    return ProjectResponse(**updated)


# -------------------------------------------------------------------
# 5. UPDATE AGENT IDENTITIES (Recorder, Builder, Executor)
# -------------------------------------------------------------------
@router.patch("/{project_id}/agents")
async def update_agent_identities(
    project_id: str,
    agents: AgentIdentities,
    current_user=Depends(get_current_user)
):
    email = current_user.get("email")

    result = await db["projects"].update_one(
        {"project_id": project_id, "created_by": email},
        {"$set": {"agent_identities": agents.model_dump()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    return {
        "message": "Agent identities updated successfully",
        "agents": agents
    }


# -------------------------------------------------------------------
# 6. DELETE PROJECT
# -------------------------------------------------------------------
@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user=Depends(get_current_user)
):
    email = current_user.get("email")

    result = await db["projects"].delete_one({"project_id": project_id, "created_by": email})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    return {"message": "Project deleted successfully"}