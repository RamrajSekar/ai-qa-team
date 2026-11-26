import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.db.connection import db
from app.services.account_billing import billing_account
from app.services.billing.registry import billing_providers
from app.services.billing.service import BillingService
from app.services.customer_accounts import CustomerAccounts
from app.utils.auth_dependency import get_current_user
from app.utils.safe_validation_route import SafeValidationRoute

router = APIRouter(tags=["Account billing"], route_class=SafeValidationRoute)


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: Literal["team", "business"]
    request_id: str = Field(pattern=r"^[0-9a-f]{32}$")


async def scoped(user, *, admin=False):
    service = CustomerAccounts(db)
    await (service.admin(user) if admin else service.require(user))
    account = await billing_account(db, user)
    if not account:
        raise HTTPException(409, "Account billing adoption is required.")
    return account


@router.get("/account/billing")
async def status(response: Response, user=Depends(get_current_user)):
    account = await scoped(user)
    provider_name = account.get("billing", {}).get("provider", settings.billing.provider)
    response.headers["Cache-Control"] = "private, no-store"
    async with billing_providers.active(provider_name) as provider:
        return await BillingService(db, provider).status(account)


@router.post("/account/billing/checkout")
async def checkout(payload: CheckoutRequest, response: Response, user=Depends(get_current_user)):
    account = await scoped(user, admin=True)
    response.headers["Cache-Control"] = "private, no-store"
    try:
        async with billing_providers.active(settings.billing.provider) as provider:
            return await BillingService(db, provider).checkout(account, user, payload.plan, payload.request_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Billing could not be confirmed. Review the saved request before retrying.") from None


@router.post("/account/billing/portal")
async def portal(response: Response, user=Depends(get_current_user)):
    account = await scoped(user, admin=True)
    billing = account.get("billing", {})
    if not billing.get("customer_id") or not billing.get("provider"):
        raise HTTPException(409, "No provider subscription is linked to this account.")
    response.headers["Cache-Control"] = "private, no-store"
    try:
        async with billing_providers.active(billing["provider"]) as provider:
            return {"url": await provider.portal(billing["customer_id"])}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Billing management is temporarily unavailable.") from None


@router.post("/billing/webhooks/{provider_name}")
async def webhook(provider_name: str, request: Request):
    if provider_name != "stripe":
        raise HTTPException(404, "Unknown billing provider.")
    provider = billing_providers.resolve(provider_name)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 256 * 1024:
            raise HTTPException(413, "Billing event exceeds the supported size.")
        chunks.append(chunk)
    try:
        event = provider.verify_event(b"".join(chunks), request.headers.get("stripe-signature", ""))
        if not re.fullmatch(r"evt_[A-Za-z0-9]+", event.get("id", "")):
            raise HTTPException(400, "Invalid billing event identity.")
        service = BillingService(db, provider)
        for action in await provider.normalize_event(event):
            if action.action == "paid": await service.paid(action.event_id, action.object_id)
            elif action.action == "subscription": await service.subscription_changed(action.event_id, action.object_id)
            elif action.action == "review": await service.payment_review(action.event_id, action.object_id, action.reason)
            elif action.action == "expired": await service.expired(action.object_id)
        return {"received": True}
    except HTTPException:
        raise
    except Exception:
        # No raw payloads, signatures, customer objects or provider exceptions in logs/errors.
        raise HTTPException(503, "Billing event requires retry or reconciliation.") from None
    finally:
        close = getattr(provider, "aclose", None)
        if close is not None:
            await close()
