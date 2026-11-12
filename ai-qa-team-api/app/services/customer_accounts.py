"""Customer ownership only. Subscription and display-ID migration are separate work."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config import settings


def enabled():
    return settings.features.customer_accounts


def email_key(value):
    return str(value or "").strip().lower()


def now():
    return datetime.now(timezone.utc)


def token_digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class CustomerAccounts:
    def __init__(self, database):
        self.db = database

    async def require(self, user):
        # Always reload authoritative assignment; client/JWT role claims are not authority.
        identity = {"_id": ObjectId(user["_id"])} if ObjectId.is_valid(str(user.get("_id", ""))) else {"email": email_key(user.get("email"))}
        stored = await self.db["users"].find_one(identity)
        if not stored or not stored.get("account_id") or stored.get("account_state") != "ACTIVE":
            raise HTTPException(409, "Customer account setup or migration is required.")
        account = await self.db["customer_accounts"].find_one({"_id": stored["account_id"], "status": "ACTIVE"})
        if not account:
            raise HTTPException(403, "Customer account is unavailable.")
        user.update({key: stored.get(key) for key in ("account_id", "account_role", "account_state")})
        return account

    async def admin(self, user):
        account = await self.require(user)
        if user.get("account_role") not in ("OWNER", "ADMIN"):
            raise HTTPException(403, "Customer account administrator access required.")
        return account

    async def project(self, project, user):
        account = await self.require(user)
        if not project or project.get("account_id") != account["_id"]:
            raise HTTPException(404, "Project not found or access denied")
        return account

    async def register(self, document, invitation_token=None, verified_email=False):
        """Provision only during new signup, never on ordinary login.

        Failures leave a non-login-capable PROVISIONING user for explicit repair.
        Invitation claim/revocation races resolve atomically before assignment.
        """
        email = email_key(document["email"])
        if await self.db["users"].find_one({"email": email}):
            raise HTTPException(409, "A user with this email already exists.")
        identity = ObjectId()
        invite = None
        pending = await self.db["account_invitations"].find_one({"_id": email})
        if pending and pending.get("status") != "PENDING":
            # A concurrent or interrupted claim must never create a second customer.
            raise HTTPException(409, "Invitation acceptance needs administrative reconciliation.")
        if invitation_token or pending:
            # Motor's default BSON decoding returns naive UTC datetimes.
            expiry = pending["expires_at"] if pending else None
            if expiry is not None and expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry is None or expiry <= now():
                raise HTTPException(409, "Invitation is unavailable or expired.")
            if not verified_email and (not invitation_token or not secrets.compare_digest(pending["token_digest"], token_digest(invitation_token))):
                raise HTTPException(403, "Use the account invitation link to sign up.")
            if not await self.db["customer_accounts"].find_one({"_id": pending["account_id"], "status": "ACTIVE"}):
                raise HTTPException(403, "Customer account is unavailable.")
            invite = await self.db["account_invitations"].find_one_and_update(
                {"_id": email, "status": "PENDING", "invitation_id": pending["invitation_id"], "expires_at": {"$gt": now()}},
                {"$set": {"status": "CLAIMED", "claim_user_id": str(identity)}}, return_document=ReturnDocument.AFTER)
            if not invite:
                raise HTTPException(409, "Invitation changed. Request a new invitation.")
        account_id = invite["account_id"] if invite else "ACC_" + uuid4().hex
        document.update({"_id": identity, "email": email, "account_id": account_id,
                         "account_role": invite["role"] if invite else "OWNER", "account_state": "PROVISIONING"})
        if invite:
            # Invited members do not create an independent project/account through setup.
            document["onboarding"] = {"onboarding_status": "completed", "current_step": 99, "steps": {}, "context": {"project_id": None, "environment_id": None}}
        try:
            await self.db["users"].insert_one(document)
        except DuplicateKeyError:
            if invite:
                await self.db["account_invitations"].update_one({"_id": email, "status": "CLAIMED", "claim_user_id": str(identity)}, {"$set": {"status": "PENDING"}})
            raise HTTPException(409, "A user with this email already exists.") from None
        if invite:
            result = await self.db["account_invitations"].update_one(
                {"_id": email, "status": "CLAIMED", "claim_user_id": str(identity)},
                {"$set": {"status": "ACCEPTED", "accepted_at": now()}})
            if result.modified_count != 1:
                raise HTTPException(409, "Invitation acceptance needs administrative reconciliation.")
        else:
            from app.services.account_billing import initial_subscription
            await self.db["customer_accounts"].insert_one({"_id": account_id, "name": None, "setup_status": "PENDING",
                "status": "ACTIVE", "owner_user_id": str(identity), "created_at": now(),
                **({"billing_version": 1, "subscription": initial_subscription(document.get("subscription"))} if settings.features.account_subscriptions else {})})
        activated = await self.db["users"].update_one({"_id": identity, "account_state": "PROVISIONING"}, {"$set": {"account_state": "ACTIVE"}})
        if activated.matched_count != 1:
            raise HTTPException(409, "Account provisioning needs administrative reconciliation.")
        document["account_state"] = "ACTIVE"
        return document

    @staticmethod
    def public(account):
        return {"account_id": account["_id"], "name": account.get("name"), "setup_status": account["setup_status"], "status": account["status"]}

    async def name(self, user, name):
        account = await self.admin(user)
        result = await self.db["customer_accounts"].update_one({"_id": account["_id"], "status": "ACTIVE"},
            {"$set": {"name": name, "setup_status": "COMPLETE", "updated_at": now()}})
        if result.matched_count != 1:
            raise HTTPException(409, "Account changed. Reload before saving.")
        return self.public({**account, "name": name, "setup_status": "COMPLETE"})

    async def invite(self, user, email, role):
        account = await self.admin(user)
        email = email_key(email)
        if role == "ADMIN" and user["account_role"] != "OWNER":
            raise HTTPException(403, "Only the account owner can invite account administrators.")
        if await self.db["users"].find_one({"email": email}):
            raise HTTPException(409, "This identity already has an account. Use project membership for existing account members.")
        token = secrets.token_urlsafe(32)
        document = {"_id": email, "invitation_id": uuid4().hex, "account_id": account["_id"], "role": role,
            "status": "PENDING", "token_digest": token_digest(token), "created_at": now(), "expires_at": now() + timedelta(days=7),
            "invited_by": str(user.get("_id") or user.get("email"))}
        from app.services.account_billing import billing_account, change_seats
        billing = await billing_account(self.db, user)
        if billing:
            await change_seats(self.db, billing, 1)
            document["account_seat_reserved"] = True
        try:
            # A global email key prevents invitations to two customer accounts racing.
            await self.db["account_invitations"].insert_one(document)
        except DuplicateKeyError:
            if billing:
                await change_seats(self.db, billing, -1)
            raise HTTPException(409, "An invitation for this identity already exists. Revoke it before inviting again.") from None
        return {"invitation_id": document["invitation_id"], "email": email, "expires_at": document["expires_at"], "token": token}

    async def revoke(self, user, invitation_id):
        account = await self.admin(user)
        pending = await self.db["account_invitations"].find_one({"account_id": account["_id"], "invitation_id": invitation_id, "status": "PENDING"})
        result = await self.db["account_invitations"].delete_one({"account_id": account["_id"], "invitation_id": invitation_id, "status": "PENDING"})
        if result.deleted_count != 1:
            raise HTTPException(409, "Invitation is not pending in this account.")
        if pending:
            from app.services.account_billing import billing_account, change_seats
            billing = await billing_account(self.db, user)
            if billing:
                await change_seats(self.db, billing, -1)
