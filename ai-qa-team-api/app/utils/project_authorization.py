from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.connection import db
from app.services.story_service import get_next_sequence
from app.services.customer_accounts import CustomerAccounts, enabled as accounts_enabled


ADMIN = "ADMIN"
TESTER = "TESTER"


def user_id(user: dict) -> str:
    return str(user.get("_id") or user.get("id") or "")


async def ensure_creator_membership(project: dict, user: dict) -> dict | None:
    """Lazily backfill an ADMIN membership when legacy ownership is unambiguous."""
    if accounts_enabled() or user.get("account_id") or project.get("account_id"):
        await CustomerAccounts(db).project(project, user)
    email = user.get("email", "").strip().lower()
    if project.get("created_by", "").strip().lower() != email:
        return None
    existing = await db["project_memberships"].find_one({"project_id": project["project_id"], "email": email})
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    membership = {
        "membership_id": await get_next_sequence("membership_id", "MEM"),
        "project_id": project["project_id"],
        **({"account_id": project["account_id"]} if project.get("account_id") else {}),
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
    await db["project_memberships"].update_one(
        {"project_id": project["project_id"], "email": email},
        {"$setOnInsert": membership},
        upsert=True,
    )
    return await db["project_memberships"].find_one({"project_id": project["project_id"], "email": email}) or membership


async def require_project_member(project_id: str, user: dict) -> tuple[dict, dict]:
    project = await db["projects"].find_one({"project_id": project_id})
    if not project:
        raise HTTPException(404, "Project not found or access denied")
    if accounts_enabled() or user.get("account_id") or project.get("account_id"):
        await CustomerAccounts(db).project(project, user)
    email = user.get("email", "").strip().lower()
    membership = await db["project_memberships"].find_one({
        "project_id": project_id, "email": email, "status": "ACTIVE",
    })
    if not membership:
        membership = await ensure_creator_membership(project, user)
    if not membership or membership.get("status") != "ACTIVE":
        raise HTTPException(404, "Project not found or access denied")
    return project, membership


async def require_project_admin(project_id: str, user: dict) -> tuple[dict, dict]:
    project, membership = await require_project_member(project_id, user)
    if membership.get("role") != ADMIN:
        raise HTTPException(403, "Project administrator access required")
    return project, membership
