"""Account-owned checkout operations, verified payment receipts and entitlements.

Provider object IDs are tenant-bound before checkout; return URLs never grant plans.
Only initial subscriptions/whole monthly renewals are supported. Plan proration and
additional-seat/request-pack purchases remain unavailable.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import secrets
import string

from fastapi import HTTPException

from app.config import settings
from app.services.account_entitlements import entitlement_limits
from app.services.billing.configuration import require_configuration
from app.services.resource_quota import ResourceQuota, fingerprint


def timestamp():
    return int(datetime.now(timezone.utc).timestamp())


class BillingService:
    def __init__(self, database, provider):
        self.db = database
        self.provider = provider
        self.quota = ResourceQuota(database)

    async def fence(self, identity, session):
        await self.db["billing_event_fences"].update_one({"_id": identity}, {"$inc": {"revision": 1}}, upsert=True, session=session)

    async def status(self, account):
        available = False
        try:
            require_configuration()
            control = await self.db["ai_spend_control"].find_one({"_id": "managed", "initialized": True, "halted": False,
                "cutover_id": settings.managed_spend.cutover_id})
            available = bool(control and account["subscription"].get("entitlement_version") == 2
                and account["subscription"].get("ai_allowance_version") == 1 and account["subscription"].get("plan") == "free")
        except HTTPException:
            pass
        billing = account.get("billing", {})
        operation = await self.db["billing_checkout_operations"].find_one({"_id": billing.get("checkout_operation"), "account_id": account["_id"]}) if billing.get("checkout_operation") else None
        return {"checkout_available": available, "test_mode": settings.billing.mode == "test",
            "hosted_domains": self.provider.hosted_domains,
            "portal_available": bool(billing.get("customer_id") and settings.billing.stripe_portal_configuration and billing.get("provider") == self.provider.name),
            "state": billing.get("status", "unconfigured"), "paid_until": billing.get("paid_until"),
            "pending": {"request_id": operation["request_id"], "plan": operation["plan"], "state": operation["state"]} if operation else None}

    async def checkout(self, account, user, plan, request_id):
        config = require_configuration()
        operation_id = fingerprint([account["_id"], request_id])
        price_id = config.stripe_price_ids[plan]
        price = await self.provider.price(price_id)
        expected = getattr(settings.pricing, plan).monthly_usd * 100
        if (price.get("active") is not True or price.get("currency") != "usd" or price.get("unit_amount") != expected
                or price.get("type") != "recurring" or price.get("recurring", {}).get("interval") != "month"
                or price.get("recurring", {}).get("interval_count") != 1 or price.get("livemode") != (config.mode == "live")):
            raise HTTPException(409, "The plan price requires billing review.")

        async def begin(session):
            row = await self.db["customer_accounts"].find_one({"_id": account["_id"], "status": "ACTIVE", "billing_version": 1}, session=session)
            if not row:
                raise HTTPException(403, "Account is unavailable.")
            existing = await self.db["billing_checkout_operations"].find_one({"_id": operation_id}, session=session)
            if existing:
                if existing["plan"] != plan or existing["account_id"] != account["_id"]:
                    raise HTTPException(409, "Checkout request does not match its saved plan.")
                if existing["state"] in ("FAILED", "FULFILLED", "EXPIRED"):
                    raise HTTPException(409, "This checkout is closed. Refresh billing status.")
                if existing["created_at"] + 23 * 3600 < timestamp():
                    raise HTTPException(409, "An uncertain checkout requires reconciliation before another purchase.")
                return existing
            sub, billing = row.get("subscription", {}), row.get("billing", {})
            if (sub.get("plan") != "free" or sub.get("status") != "active" or sub.get("entitlement_version") != 2
                    or sub.get("ai_allowance_version") != 1 or billing.get("checkout_operation") or billing.get("status") in ("active", "past_due", "review_required")):
                raise HTTPException(409, "Review the current account subscription or pending checkout before purchasing.")
            control = await self.db["ai_spend_control"].find_one({"_id": "managed", "initialized": True, "halted": False,
                "cutover_id": settings.managed_spend.cutover_id}, session=session)
            if not control:
                raise HTTPException(503, "Managed AI spend cutover requires review.")
            operation = {"_id": operation_id, "request_id": request_id, "account_id": account["_id"], "actor_id": str(user["_id"]),
                "provider": self.provider.name, "livemode": config.mode == "live", "plan": plan, "price_id": price_id,
                "monthly_cents": expected, "limits": entitlement_limits(sub, plan), "state": "CREATING", "created_at": timestamp(),
                "expires_at": timestamp() + 24 * 3600,
                "integration_identifier": "ai-qa-team-" + "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))}
            await self.db["billing_checkout_operations"].insert_one(operation, session=session)
            await self.db["customer_accounts"].update_one({"_id": row["_id"]}, {"$set": {"billing.checkout_operation": operation_id}}, session=session)
            return operation

        operation = await self.quota.transaction(begin)
        if operation.get("url"):
            return {"url": operation["url"], "request_id": request_id}
        if operation["expires_at"] < timestamp() + 30 * 60:
            raise HTTPException(409, "Checkout needs reconciliation. Do not create a second purchase.")
        try:
            key = fingerprint([self.provider.name, operation["livemode"], account["_id"]])
            link = await self.db["billing_account_customers"].find_one({"_id": key})
            customer_id = link["customer_id"] if link else await self.provider.create_customer(account["_id"], operation_id)

            async def bind_customer(session):
                await self.db["billing_account_customers"].update_one({"_id": key}, {"$setOnInsert": {
                    "account_id": account["_id"], "customer_id": customer_id, "provider": self.provider.name,
                    "livemode": operation["livemode"]}}, upsert=True, session=session)
                await self.db["billing_customer_owners"].update_one({"_id": fingerprint([self.provider.name, operation["livemode"], customer_id])},
                    {"$setOnInsert": {"account_id": account["_id"], "customer_id": customer_id}}, upsert=True, session=session)
                await self.db["billing_checkout_operations"].update_one({"_id": operation_id}, {"$set": {"customer_id": customer_id}}, session=session)
            await self.quota.transaction(bind_customer)
            result = await self.provider.checkout(operation, customer_id)
            await self.db["billing_checkout_operations"].update_one({"_id": operation_id, "state": {"$in": ["CREATING", "UNKNOWN"]}},
                {"$set": {"state": "READY", "session_id": result["id"], "url": result["url"]}})
            return {"url": result["url"], "request_id": request_id}
        except Exception:
            await self.db["billing_checkout_operations"].update_one({"_id": operation_id, "state": {"$in": ["CREATING", "UNKNOWN"]}}, {"$set": {"state": "UNKNOWN"}})
            raise HTTPException(502, "Checkout could not be confirmed. Resume the saved request; do not create another purchase.") from None

    async def paid(self, event_id, invoice_id):
        invoice = await self.provider.paid_invoice(invoice_id)
        if not invoice.current or invoice.reason not in ("subscription_create", "subscription_cycle"):
            return {"ignored": True}
        if (not isinstance(invoice.paid_until, int) or isinstance(invoice.paid_until, bool)
                or invoice.paid_until <= timestamp()):
            raise HTTPException(409, "The paid subscription period requires billing review.")
        owner = await self.db["billing_customer_owners"].find_one({"_id": fingerprint([self.provider.name, invoice.livemode, invoice.customer_id])})
        if not owner:
            return {"ignored": True}
        receipt_id = fingerprint([self.provider.name, invoice.livemode, invoice.invoice_id])
        binding_id = fingerprint([self.provider.name, invoice.livemode, invoice.subscription_id])

        async def apply(session):
            await self.fence(binding_id, session)
            await self.fence(receipt_id, session)
            if await self.db["billing_payment_receipts"].find_one({"_id": receipt_id}, session=session):
                return {"duplicate": True}
            if (await self.db["billing_subscription_stops"].find_one({"_id": binding_id}, session=session)
                    or await self.db["billing_invoice_reviews"].find_one({"_id": receipt_id}, session=session)):
                raise HTTPException(409, "This subscription or payment requires billing review.")
            account = await self.db["customer_accounts"].find_one({"_id": owner["account_id"], "status": "ACTIVE", "billing_version": 1}, session=session)
            if not account:
                raise HTTPException(409, "The account requires billing review.")
            binding = await self.db["billing_subscriptions"].find_one({"_id": binding_id, "account_id": owner["account_id"]}, session=session)
            if not binding:
                operation = await self.db["billing_checkout_operations"].find_one({"_id": account.get("billing", {}).get("checkout_operation"),
                    "account_id": owner["account_id"], "customer_id": invoice.customer_id, "price_id": invoice.price_id,
                    "livemode": invoice.livemode, "state": {"$in": ["READY", "CREATING", "UNKNOWN"]}}, session=session)
                if not operation:
                    raise HTTPException(409, "The payment does not match a reviewed checkout.")
                binding = {"_id": binding_id, "account_id": owner["account_id"], "provider": self.provider.name,
                    "provider_subscription_id": invoice.subscription_id, "customer_id": invoice.customer_id,
                    "price_id": operation["price_id"], "plan": operation["plan"], "limits": operation["limits"],
                    "monthly_cents": operation["monthly_cents"], "livemode": invoice.livemode}
                await self.db["billing_subscriptions"].insert_one(binding, session=session)
                await self.db["billing_checkout_operations"].update_one({"_id": operation["_id"]}, {"$set": {"state": "FULFILLED"}}, session=session)
            prior = account.get("billing", {})
            if (binding["price_id"] != invoice.price_id or invoice.currency != "usd" or invoice.subtotal != binding["monthly_cents"]
                    or invoice.amount_paid < binding["monthly_cents"] or prior.get("status") == "review_required"
                    or prior.get("subscription_id") not in (None, binding_id)):
                raise HTTPException(409, "This payment requires billing review.")
            before = account["subscription"]
            if before.get("entitlement_version") != 2 or before.get("ai_allowance_version") != 1:
                raise HTTPException(409, "Versioned account adoption is required.")
            billing = {"provider": self.provider.name, "subscription_id": binding_id, "customer_id": invoice.customer_id,
                "provider_subscription_id": invoice.subscription_id, "livemode": invoice.livemode, "status": "active",
                "paid_until": max(prior.get("paid_until", 0), invoice.paid_until), "latest_paid_invoice": invoice.invoice_id,
                "managed_spend_required": True}
            await self.db["customer_accounts"].update_one({"_id": account["_id"]}, {"$set": {"billing": billing,
                "subscription.plan": binding["plan"], "subscription.limits": binding["limits"]}}, session=session)
            await self.db["billing_payment_receipts"].insert_one({"_id": receipt_id, "account_id": account["_id"],
                "event_id": event_id, "invoice": asdict(invoice), "binding_id": binding_id,
                "before_plan": before["plan"], "at": datetime.now(timezone.utc)}, session=session)
            return {"applied": True}
        return await self.quota.transaction(apply)

    async def subscription_changed(self, event_id, subscription_id):
        current = await self.provider.subscription(subscription_id)
        mode = bool(current.get("livemode"))
        binding_id = fingerprint([self.provider.name, mode, subscription_id])
        state = current.get("status")
        if state not in ("active", "past_due", "unpaid", "canceled", "incomplete_expired", "paused"):
            return {"ignored": True}
        identity = fingerprint([self.provider.name, event_id])

        async def apply(session):
            await self.fence(binding_id, session)
            if state in ("canceled", "incomplete_expired"):
                await self.db["billing_subscription_stops"].update_one({"_id": binding_id}, {"$setOnInsert": {
                    "provider": self.provider.name, "subscription_id": subscription_id,
                    "state": state, "event_id": event_id}}, upsert=True, session=session)
            if await self.db["billing_state_receipts"].find_one({"_id": identity}, session=session):
                return {"duplicate": True}
            binding = await self.db["billing_subscriptions"].find_one({"_id": binding_id}, session=session)
            if not binding:
                return {"ignored": True}
            account = await self.db["customer_accounts"].find_one({"_id": binding["account_id"], "billing.subscription_id": binding_id}, session=session)
            if not account:
                return {"ignored": True}
            changes = {"billing.cancel_at_period_end": bool(current.get("cancel_at_period_end"))}
            if state != "active":
                changes["billing.status"] = "ended" if state in ("canceled", "incomplete_expired") else "past_due"
                if state in ("canceled", "incomplete_expired"):
                    changes.update({"subscription.plan": "free", "subscription.limits": entitlement_limits(account["subscription"], "free")})
            await self.db["customer_accounts"].update_one({"_id": account["_id"]}, {"$set": changes}, session=session)
            await self.db["billing_state_receipts"].insert_one({"_id": identity, "account_id": account["_id"],
                "provider_subscription_id": subscription_id, "state": state, "at": datetime.now(timezone.utc)}, session=session)
            return {"applied": True}
        return await self.quota.transaction(apply)

    async def payment_review(self, event_id, invoice_id, reason):
        receipt_id = fingerprint([self.provider.name, settings.billing.mode == "live", invoice_id])
        async def apply(session):
            await self.fence(receipt_id, session)
            await self.db["billing_invoice_reviews"].update_one({"_id": receipt_id}, {"$setOnInsert": {
                "provider": self.provider.name, "event_id": event_id, "reason": reason}}, upsert=True, session=session)
            receipt = await self.db["billing_payment_receipts"].find_one({"_id": receipt_id}, session=session)
            if not receipt:
                return {"ignored": True}
            identity = fingerprint([self.provider.name, event_id])
            if await self.db["billing_state_receipts"].find_one({"_id": identity}, session=session):
                return {"duplicate": True}
            await self.db["customer_accounts"].update_one({"_id": receipt["account_id"], "billing.latest_paid_invoice": invoice_id},
                {"$set": {"billing.status": "review_required", "billing.review_reason": reason}}, session=session)
            await self.db["billing_state_receipts"].insert_one({"_id": identity, "account_id": receipt["account_id"], "invoice_id": invoice_id,
                "reason": reason, "at": datetime.now(timezone.utc)}, session=session)
            return {"review_required": True}
        return await self.quota.transaction(apply)

    async def expired(self, session_id):
        async def apply(session):
            operation = await self.db["billing_checkout_operations"].find_one({"provider": self.provider.name,
                "session_id": session_id, "state": {"$in": ["READY", "UNKNOWN"]}}, session=session)
            if not operation:
                return {"ignored": True}
            await self.db["billing_checkout_operations"].update_one({"_id": operation["_id"]}, {"$set": {"state": "EXPIRED"}}, session=session)
            await self.db["customer_accounts"].update_one({"_id": operation["account_id"], "billing.checkout_operation": operation["_id"]},
                {"$unset": {"billing.checkout_operation": ""}}, session=session)
            return {"expired": True}
        return await self.quota.transaction(apply)
