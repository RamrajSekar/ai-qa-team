from fastapi import APIRouter, Depends, HTTPException
from app.db.connection import db
from bson.objectid import ObjectId
from app.models.project_model import AgentIdentities
from app.utils.auth_dependency import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.patch("/{project_id}/agents")
async def update_agent_identities(
    project_id: str,
    agents: AgentIdentities,
    current_user=Depends(get_current_user)
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID")

    result = await db["projects"].update_one(
        {"_id": ObjectId(project_id), "created_by": current_user["email"]},
        {"$set": {"agent_identities": agents.model_dump()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    return {"message": "Agent identities updated successfully", "agents": agents}
