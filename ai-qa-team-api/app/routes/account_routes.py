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
    return [{key: doc[key] for key in ("invitation_id", "expires_at", "role")} | {"email": doc["_id"]} for doc in docs]


@router.post("/invitations", status_code=201)
async def invite(payload: Invitation, response: Response, user=Depends(get_current_user)):
    response.headers["Cache-Control"] = "private, no-store"
    # The invitation credential is returned once to its administrator, never in lists/logs.
    return await CustomerAccounts(db).invite(user, str(payload.email), payload.role)


@router.delete("/invitations/{invitation_id}")
async def revoke(invitation_id: str, user=Depends(get_current_user)):
    await CustomerAccounts(db).revoke(user, invitation_id)
    return {"revoked": True}
