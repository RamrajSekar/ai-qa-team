from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.connection import db
from app.services.customer_accounts import CustomerAccounts
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.safe_validation_route import SafeValidationRoute

router = APIRouter(prefix="/account", tags=["Customer account"], route_class=SafeValidationRoute,
                   dependencies=[Depends(feature_required("customer_accounts"))])


class AccountName(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=160)


class Invitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    role: Literal["ADMIN", "MEMBER"] = "MEMBER"
    delivery: Literal["LINK", "EMAIL"] = "LINK"


@router.get("")
async def current(response: Response, user=Depends(get_current_user)):
    response.headers["Cache-Control"] = "private, no-store"
    service = CustomerAccounts(db)
    return {**service.public(await service.require(user)), "current_user_role": user["account_role"]}


@router.patch("")
async def rename(payload: AccountName, user=Depends(get_current_user)):
    return await CustomerAccounts(db).name(user, payload.name)


@router.get("/members")
async def members(response: Response, user=Depends(get_current_user)):
    account = await CustomerAccounts(db).require(user)
    response.headers["Cache-Control"] = "private, no-store"
    docs = await db["users"].find({"account_id": account["_id"], "account_state": "ACTIVE"},
        {"name": 1, "email": 1, "account_role": 1}).to_list(500)
    return [{"name": doc.get("name"), "email": doc["email"], "account_role": doc["account_role"]} for doc in docs]


@router.get("/projects")
async def managed_projects(response: Response, user=Depends(get_current_user)):
    account = await CustomerAccounts(db).admin(user)
    response.headers["Cache-Control"] = "private, no-store"
    docs = await db["projects"].find({"account_id": account["_id"]}, {"project_id": 1, "name": 1}).to_list(500)
    return [{"project_id": doc["project_id"], "name": doc.get("name", doc["project_id"])} for doc in docs]


@router.get("/subscription")
async def account_subscription(response: Response, user=Depends(get_current_user)):
    account = await CustomerAccounts(db).require(user)
    from app.services.account_billing import billing_account
    billing = await billing_account(db, user)
    response.headers["Cache-Control"] = "private, no-store"
    if not billing:
        return {"billing_scope": "LEGACY_USER", "migration_required": True}
    return {"account_id": account["_id"], "billing_scope": "ACCOUNT", "subscription": billing["subscription"]}


@router.get("/invitations")
async def invitations(response: Response, user=Depends(get_current_user)):
    account = await CustomerAccounts(db).admin(user)
    response.headers["Cache-Control"] = "private, no-store"
    docs = await db["account_invitations"].find({"account_id": account["_id"], "status": "PENDING"}).to_list(500)
    return [{key: doc[key] for key in ("invitation_id", "expires_at", "role")} | {"email": doc["_id"], "email_delivery": doc.get("email_delivery")} for doc in docs]


@router.post("/invitations", status_code=201)
async def invite(payload: Invitation, response: Response, user=Depends(get_current_user)):
    response.headers["Cache-Control"] = "private, no-store"
    service = CustomerAccounts(db)
    account = await service.admin(user)
    if payload.delivery == "EMAIL":
        from app.services.invitation_email import require_configuration, send_invitation
        require_configuration()  # No invitation or seat is created when unavailable.
    invitation = await service.invite(user, str(payload.email), payload.role)
    if payload.delivery == "LINK":
        # Manual credentials are returned once; email mode never exposes the token.
        return invitation
    identity = {"account_id": account["_id"], "invitation_id": invitation["invitation_id"]}
    await db["account_invitations"].update_one(identity, {"$set": {"email_delivery": "SENDING"}})
    try:
        await send_invitation(invitation["email"], invitation["token"], account.get("name"))
    except Exception:
        # A timeout can occur after SMTP accepted the email. Retain the invitation
        # and seat; never blindly resend, revoke or fall back to another delivery.
        await db["account_invitations"].update_one(identity, {"$set": {"email_delivery": "UNKNOWN"}})
        from fastapi import HTTPException
        raise HTTPException(502, "Email delivery could not be confirmed. Review the pending invitation before revoking or trying again.") from None
    await db["account_invitations"].update_one(identity, {"$set": {"email_delivery": "SENT"}})
    return {key: value for key, value in invitation.items() if key != "token"} | {"email_delivery": "SENT"}


@router.delete("/invitations/{invitation_id}")
async def revoke(invitation_id: str, user=Depends(get_current_user)):
    await CustomerAccounts(db).revoke(user, invitation_id)
    return {"revoked": True}
