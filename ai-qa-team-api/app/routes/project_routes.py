from fastapi import APIRouter, Depends, HTTPException
from app.db.connection import db
from bson.objectid import ObjectId
from datetime import datetime, timezone
from app.models.project_model import AgentIdentities
from app.utils.auth_dependency import get_current_user
from app.services.story_service import get_next_sequence
from app.models.project_model import ProjectCreate, ProjectResponse, AgentIdentities
from app.utils.subscription_dependency import subscription_required
from app.services.project_team_service import create_creator_membership
from app.services.customer_accounts import CustomerAccounts, enabled as accounts_enabled
from app.services.subscription_services import increment_usage, decrement_usage
from app.utils.project_authorization import require_project_admin, require_project_member

router = APIRouter(prefix="/projects", tags=["Projects"])


# -------------------------------------------------------------------
# 1. CREATE PROJECT
# -------------------------------------------------------------------
@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user=Depends(get_current_user),
    _: None = Depends(subscription_required("projects"))
):
    account = None
    if accounts_enabled() or current_user.get("account_id"):
        account = await CustomerAccounts(db).admin(current_user)
        if account.get("setup_status") != "COMPLETE":
            raise HTTPException(409, "Name the customer account in onboarding before creating a project.")
    # Generate next project ID
    new_project_id = await get_next_sequence("project_id", "PRJ")

    data = project.model_dump()
    if account:
        data["account_id"] = account["_id"]
    if account:
        # Display numbering is account-local; canonical route IDs stay globally unique.
        while True:
            display_id = await get_next_sequence(f"account:{account['_id']}:project_display_id", "PRJ")
            # Reserve legacy labels too, without renumbering existing projects.
            legacy = await db["projects"].find_one({"account_id": account["_id"], "project_id": display_id})
            if not legacy:
                data["display_id"] = display_id
                break
    data["project_id"] = new_project_id
    data["created_by"] = current_user["email"]
    data["created_at"] = datetime.now(timezone.utc).isoformat()

    # Ensure agent identities stored as dict
    if hasattr(project, "agent_identities"):
        data["agent_identities"] = project.agent_identities.model_dump()
    else:
        data["agent_identities"] = {}

    # Insert the project and its creator membership as one logical operation.
    # Standalone Mongo installations may not support transactions, so compensate
    # by removing the project if membership creation fails.
    result = await db["projects"].insert_one(data)
    data["id"] = str(result.inserted_id)
    try:
        await create_creator_membership(new_project_id, current_user)
    except Exception:
        await db["projects"].delete_one({"project_id": new_project_id})
        raise
    data["current_user_role"] = "ADMIN"

    # ðŸ”¥ Increment project usage (FIXES DASHBOARD & /projects)
    from app.services.account_billing import billing_account
    billing = await billing_account(db, current_user)
    if billing:
        await db["customer_accounts"].update_one({"_id": billing["_id"]}, {"$inc": {"subscription.usage.projects_used": 1}})
    else:
        await db["users"].update_one({"email": current_user["email"]}, {"$inc": {"subscription.usage.projects_used": 1}})

    # ðŸ”¥ Update onboarding steps
    await db["users"].update_one(
        {"email": current_user["email"]},
        {
            "$set": {
                "onboarding.steps.project": True,
                "onboarding.current_step": 2,
                "onboarding.onboarding_status": "completed" if current_user.get("onboarding", {}).get("onboarding_status") == "completed" else "in_progress",
                "onboarding.context.project_id": data["project_id"],
                
            }
        }
    )

    return ProjectResponse(**data)


# -------------------------------------------------------------------
# 2. LIST PROJECTS FOR USER
# -------------------------------------------------------------------
@router.get("", response_model=list[ProjectResponse])
async def list_projects(current_user=Depends(get_current_user)):
    account = None
    if accounts_enabled() or current_user.get("account_id"):
        account = await CustomerAccounts(db).require(current_user)
    account_scope = {"account_id": account["_id"]} if account else {}
    account_email = current_user.get("email", "")
    email = account_email.lower()
    # Backfill only projects whose legacy creator is unambiguous.
    owned = await db["projects"].find({"created_by": account_email, **account_scope}).to_list(500)
    for project in owned:
        await require_project_member(project["project_id"], current_user)
    memberships = await db["project_memberships"].find({"email": email, "status": "ACTIVE"}).to_list(500)
    roles = {membership["project_id"]: membership["role"] for membership in memberships}
    cursor = db["projects"].find({"project_id": {"$in": list(roles)}, **account_scope})
    projects = []

    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        doc["current_user_role"] = roles.get(doc["project_id"])
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
    project, membership = await require_project_member(project_id, current_user)

    project["id"] = str(project["_id"])
    del project["_id"]
    project["current_user_role"] = membership["role"]

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
    project, _ = await require_project_admin(project_id, current_user)
    if (accounts_enabled() or project.get("account_id")) and set(data) - {"name", "description", "agent_identities"}:
        raise HTTPException(422, "Project ownership and identifiers cannot be edited.")

    update_data = {k: v for k, v in data.items() if v is not None}
    if "project_id" in update_data:
        exists = await db["projects"].find_one({"project_id": update_data["project_id"]})
        if exists and exists["project_id"] != project_id:
            raise HTTPException(400, "Project ID already exists")

    result = await db["projects"].update_one(
        {"project_id": project_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    updated = await db["projects"].find_one({"project_id": project_id})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    updated["current_user_role"] = "ADMIN"

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
    await require_project_admin(project_id, current_user)

    result = await db["projects"].update_one(
        {"project_id": project_id},
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
# @router.delete("/{project_id}")
# async def delete_project(
#     project_id: str,
#     current_user=Depends(get_current_user)
# ):
#     email = current_user.get("email")

#     result = await db["projects"].delete_one({"project_id": project_id, "created_by": email})

#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="Project not found or access denied")

#     return {"message": "Project deleted successfully"}

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user=Depends(get_current_user)
):
    project, _ = await require_project_admin(project_id, current_user)
    email = project["created_by"]

    result = await db["projects"].delete_one(
        {"project_id": project_id}
    )
    

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    additional_members = await db["project_memberships"].count_documents({
        "project_id": project_id,
        "email": {"$ne": email.lower()},
    })
    await db["project_memberships"].delete_many({"project_id": project_id})
    await db["ai_configurations"].delete_many({"project_id": project_id})
    await db["encrypted_secrets"].delete_many({"project_id": project_id})

    # ðŸ”¥ Decrement usage count
    from app.services.account_billing import billing_account
    billing = await billing_account(db, current_user)
    if billing:
        await decrement_usage(current_user["email"], "projects_used")
    else:
        await db["users"].update_one({"email": email}, {"$inc": {
            "subscription.usage.projects_used": -1, "subscription.usage.team_members_used": -additional_members}})

    # Deleting the setup project abandons that wizard, not the customer account.
    await db["users"].update_many(
        {"onboarding.context.project_id": project_id},
        {"$set": {"onboarding.context.project_id": None,
                  "onboarding.context.environment_id": None,
                  "onboarding.onboarding_status": "completed",
                  "onboarding.current_step": 99}}
    )

    return {"message": "Project deleted successfully"}
