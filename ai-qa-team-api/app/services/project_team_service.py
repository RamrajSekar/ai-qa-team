from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.db.connection import db
from app.services.story_service import get_next_sequence
from app.services.subscription_services import decrement_usage, get_subscription, increment_usage
from app.services.customer_accounts import CustomerAccounts, enabled as accounts_enabled
from app.utils.project_authorization import ADMIN, require_project_admin, require_project_member, user_id


async def require_team_admin(project_id, current_user):
    if accounts_enabled() or current_user.get("account_id"):
        service = CustomerAccounts(db)
        await service.admin(current_user)
        project = await db["projects"].find_one({"project_id": project_id})
        await service.project(project, current_user)
        return project, {"role": ADMIN}
    return await require_project_admin(project_id, current_user)


def public_membership(document: dict, user: dict | None = None) -> dict:
    return {
        "membership_id": document["membership_id"],
        "project_id": document["project_id"],
        "user_id": document.get("user_id"),
        "email": document["email"],
        "name": (user or {}).get("name"),
        "role": document["role"],
        "status": document["status"],
        "invited_by": document.get("invited_by"),
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }


async def create_creator_membership(project_id: str, user: dict) -> dict:
    now = datetime.now(timezone.utc)
    email = user["email"].strip().lower()
    membership = {
        "membership_id": await get_next_sequence("membership_id", "MEM"),
        "project_id": project_id,
        **({"account_id": user["account_id"]} if user.get("account_id") else {}),
        "user_id": user_id(user) or None,
        "email": email,
        "role": ADMIN,
        "status": "ACTIVE",
        "invited_by": email,
        "billing_owner": email,
        "counts_toward_limit": False,
        "created_at": now,
        "updated_at": now,
    }
    try:
        await db["project_memberships"].insert_one(membership)
    except DuplicateKeyError as exc:
        raise HTTPException(409, "This user already has a membership or pending invitation") from exc
    return membership


async def activate_pending_memberships(user: dict) -> int:
    email = user["email"].strip().lower()
    if accounts_enabled() or user.get("account_id"):
        account = await CustomerAccounts(db).require(user)
        # Legacy invitations are never auto-accepted into an account.
        projects = await db["projects"].find({"account_id": account["_id"]}).to_list(500)
        project_ids = [project["project_id"] for project in projects]
    else:
        project_ids = None
    result = await db["project_memberships"].update_many(
        {"email": email, "status": "INVITED", **({"project_id": {"$in": project_ids}, "account_id": user["account_id"]} if project_ids is not None else {})},
        {"$set": {"user_id": user_id(user) or None, "status": "ACTIVE", "updated_at": datetime.now(timezone.utc)}},
    )
    return result.modified_count


async def list_team(project_id: str, current_user: dict) -> dict:
    if current_user.get("account_role") in ("OWNER", "ADMIN"):
        _, current = await require_team_admin(project_id, current_user)
    else:
        _, current = await require_project_member(project_id, current_user)
        if accounts_enabled() or current_user.get("account_id"):
            current = {"role": "TESTER"}  # Account administration governs edits.
    documents = await db["project_memberships"].find({"project_id": project_id}).to_list(500)
    members = []
    for document in documents:
        profile = await db["users"].find_one({"email": document["email"]}, {"name": 1})
        members.append(public_membership(document, profile))
    return {"current_user_role": current["role"], "members": members}


async def invite_member(project_id: str, email: str, role: str, current_user: dict) -> dict:
    project, _ = await require_team_admin(project_id, current_user)
    normalized_email = email.strip().lower()
    invited_user = None
    if accounts_enabled() or project.get("account_id") or current_user.get("account_id"):
        account = await CustomerAccounts(db).project(project, current_user)
        invited_user = await db["users"].find_one({"email": normalized_email, "account_id": account["_id"], "account_state": "ACTIVE"})
        if not invited_user:
            raise HTTPException(409, "Select an existing member of this customer account. An account administrator must invite new users from Account settings.")
    if await db["project_memberships"].find_one({"project_id": project_id, "email": normalized_email}):
        raise HTTPException(409, "This user already has a membership or pending invitation")
    owner_email = project["created_by"].strip()
    from app.services.account_billing import billing_account
    billing = await billing_account(db, current_user)
    subscription = billing["subscription"] if billing else await get_subscription(owner_email)
    if not subscription:
        raise HTTPException(403, "Project owner has no active subscription")
    used = subscription.get("usage", {}).get("team_members_used", 0)
    limit = subscription.get("limits", {}).get("team_members_limit", 0)
    if not billing and limit is not None and used >= limit:
        raise HTTPException(403, "Team members limit reached. Please upgrade the project owner's plan.")
    invited_user = invited_user or await db["users"].find_one({"email": normalized_email})
    now = datetime.now(timezone.utc)
    membership = {
        "membership_id": await get_next_sequence("membership_id", "MEM"),
        "project_id": project_id,
        "user_id": str(invited_user["_id"]) if invited_user else None,
        "email": normalized_email,
        "role": role,
        "status": "ACTIVE" if invited_user else "INVITED",
        "invited_by": current_user["email"],
        "billing_owner": owner_email,
        "counts_toward_limit": not bool(billing),
        **({"account_id": project["account_id"]} if project.get("account_id") else {}),
        "created_at": now,
        "updated_at": now,
    }
    try:
        await db["project_memberships"].insert_one(membership)
    except DuplicateKeyError as exc:
        raise HTTPException(409, "This user already has a membership or pending invitation") from exc
    if not billing:
        await increment_usage(owner_email, "team_members_used")
    return public_membership(membership, invited_user)


async def _active_admin_count(project_id: str) -> int:
    return await db["project_memberships"].count_documents({
        "project_id": project_id, "role": ADMIN, "status": "ACTIVE",
    })


async def change_member_role(project_id: str, membership_id: str, role: str, current_user: dict) -> dict:
    await require_team_admin(project_id, current_user)
    membership = await db["project_memberships"].find_one({"project_id": project_id, "membership_id": membership_id})
    if not membership:
        raise HTTPException(404, "Project membership not found")
    if membership["role"] == ADMIN and role != ADMIN and membership["status"] == "ACTIVE" and await _active_admin_count(project_id) <= 1:
        raise HTTPException(409, "A project must have at least one active administrator")
    await db["project_memberships"].update_one(
        {"membership_id": membership_id}, {"$set": {"role": role, "updated_at": datetime.now(timezone.utc)}}
    )
    return public_membership({**membership, "role": role, "updated_at": datetime.now(timezone.utc)})


async def remove_member(project_id: str, membership_id: str, current_user: dict) -> None:
    project, _ = await require_team_admin(project_id, current_user)
    membership = await db["project_memberships"].find_one({"project_id": project_id, "membership_id": membership_id})
    if not membership:
        raise HTTPException(404, "Project membership not found")
    if membership["role"] == ADMIN and membership["status"] == "ACTIVE" and await _active_admin_count(project_id) <= 1:
        raise HTTPException(409, "A project must have at least one active administrator")
    await db["project_memberships"].delete_one({"membership_id": membership_id})
    from app.services.account_billing import billing_account
    billing = await billing_account(db, current_user)
    if not billing and membership["email"] != project["created_by"].strip().lower():
        await decrement_usage(project["created_by"], "team_members_used")
