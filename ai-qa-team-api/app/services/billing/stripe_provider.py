"""All Stripe objects/API calls stay inside this adapter. No raw provider errors escape."""
from urllib.parse import urlsplit

from fastapi import HTTPException
import stripe

from app.config import settings
from app.services.billing.contracts import PaidInvoice, BillingEvent

API_VERSION = "2026-11-18.endive"


def plain(value):
    return value.to_dict() if hasattr(value, "to_dict") else dict(value)


def object_id(value):
    return value.get("id") if isinstance(value, dict) else value


def hosted_url(value, host):
    url = urlsplit(value or "")
    if url.scheme != "https" or url.hostname != host or url.username or url.password or url.port not in (None, 443):
        raise HTTPException(502, "The billing provider returned an invalid hosted page.")
    return value


class StripeProvider:
    name = "stripe"
    hosted_domains = {"checkout": "checkout.stripe.com", "portal": "billing.stripe.com"}

    def __init__(self, *, client=None):
        self._client = client
        self._http = None

    async def aclose(self):
        if self._http is not None:
            await self._http.close_async()

    @property
    def client(self):
        if self._client is not None:
            return self._client
        config = settings.billing
        if not config.stripe_key:
            raise HTTPException(503, "Billing provider is not configured.")
        self._http = stripe.HTTPXClient(timeout=20)
        self._client = stripe.StripeClient(config.stripe_key.get_secret_value(), stripe_version=API_VERSION,
            http_client=self._http, max_network_retries=0)
        return self._client

    async def create_customer(self, account_id, operation_id):
        customer = await self.client.v1.customers.create_async({"metadata": {"application": "ai-qa-team", "account_id": account_id}},
            options={"idempotency_key": "customer:" + operation_id})
        return customer.id

    async def price(self, price_id):
        return plain(await self.client.v1.prices.retrieve_async(price_id))

    async def checkout(self, operation, customer_id):
        if settings.billing.mode == "live":
            await self.portal_policy()
        origin = str(settings.billing.app_origin).rstrip("/")
        params = {"mode": "subscription", "customer": customer_id,
            "line_items": [{"price": operation["price_id"], "quantity": 1}],
            "success_url": origin + "/settings/account/plans?checkout=returned",
            "cancel_url": origin + "/settings/account/plans?checkout=cancelled",
            "client_reference_id": operation["_id"], "integration_identifier": operation["integration_identifier"],
            "subscription_data": {"metadata": {"operation_id": operation["_id"]}},
            "expires_at": operation["expires_at"]}
        if settings.billing.mode == "live":
            params.update(automatic_tax={"enabled": True}, billing_address_collection="required",
                consent_collection={"terms_of_service": "required"})
        session = plain(await self.client.v1.checkout.sessions.create_async(params,
            options={"idempotency_key": "checkout:" + operation["_id"]}))
        if session.get("livemode") != (settings.billing.mode == "live"):
            raise HTTPException(502, "Billing environment mismatch.")
        return {"id": session["id"], "url": hosted_url(session["url"], "checkout.stripe.com")}

    async def portal_policy(self):
        if not settings.billing.stripe_portal_configuration:
            raise HTTPException(503, "Billing management is not configured.")
        configuration = plain(await self.client.v1.billing_portal.configurations.retrieve_async(settings.billing.stripe_portal_configuration))
        features = configuration.get("features", {})
        if (not configuration.get("active") or features.get("subscription_update", {}).get("enabled")
                or features.get("subscription_cancel", {}).get("enabled") is not True
                or features.get("subscription_cancel", {}).get("mode") != "at_period_end"):
            raise HTTPException(503, "Billing portal policy requires review.")

    async def portal(self, customer_id):
        await self.portal_policy()
        session = await self.client.v1.billing_portal.sessions.create_async({"customer": customer_id,
            "configuration": settings.billing.stripe_portal_configuration,
            "return_url": str(settings.billing.app_origin).rstrip("/") + "/settings/account/plans"})
        return hosted_url(session.url, "billing.stripe.com")

    def verify_event(self, payload, signature):
        if not settings.billing.stripe_webhook_secret:
            raise HTTPException(503, "Billing webhook is not configured.")
        try:
            event = stripe.Webhook.construct_event(payload, signature,
                settings.billing.stripe_webhook_secret.get_secret_value(), tolerance=300)
            result = plain(event)
            if result.get("account") or result.get("api_version") != API_VERSION:
                raise ValueError("Unsupported event context")
            if result.get("livemode") != (settings.billing.mode == "live"):
                raise ValueError("Environment mismatch")
            return result
        except (ValueError, stripe.SignatureVerificationError):
            raise HTTPException(400, "Invalid billing webhook.") from None

    async def subscription(self, subscription_id):
        return plain(await self.client.v1.subscriptions.retrieve_async(subscription_id))

    async def paid_invoice(self, invoice_id):
        invoice = plain(await self.client.v1.invoices.retrieve_async(invoice_id))
        subscription_id = object_id(((invoice.get("parent") or {}).get("subscription_details") or {}).get("subscription"))
        if not subscription_id or invoice.get("status") != "paid":
            raise HTTPException(409, "A paid subscription invoice is required.")
        subscription = await self.subscription(subscription_id)
        lines = invoice.get("lines", {})
        if lines.get("has_more") or len(lines.get("data", [])) != 1:
            raise HTTPException(409, "This invoice requires billing review.")
        line = lines["data"][0]
        price_id = object_id(((line.get("pricing") or {}).get("price_details") or {}).get("price"))
        if line.get("quantity") != 1 or not price_id or ((line.get("parent") or {}).get("subscription_item_details") or {}).get("proration"):
            raise HTTPException(409, "This invoice requires billing review.")
        return PaidInvoice(self.name, invoice_id, object_id(invoice.get("customer")), subscription_id,
            price_id, invoice.get("amount_paid", 0), invoice.get("subtotal", 0), invoice.get("currency", ""),
            line.get("period", {}).get("end", 0), bool(invoice.get("livemode")),
            object_id(subscription.get("latest_invoice")) == invoice_id and subscription.get("status") == "active",
            invoice.get("billing_reason", ""))

    async def invoice_for_payment(self, payment_intent_id):
        payments = plain(await self.client.v1.invoice_payments.list_async({"payment": {"type": "payment_intent", "payment_intent": payment_intent_id}, "limit": 2}))
        rows = payments.get("data", [])
        if payments.get("has_more") or len(rows) != 1:
            raise HTTPException(409, "The payment requires billing review.")
        return object_id(rows[0].get("invoice"))

    async def normalize_event(self, event):
        kind, identity = event.get("type"), event["id"]
        reference = event.get("data", {}).get("object", {}).get("id")
        if not reference:
            raise HTTPException(400, "Invalid billing event.")
        if kind == "invoice.paid":
            return [BillingEvent(identity, "paid", reference)]
        if kind in ("customer.subscription.updated", "customer.subscription.deleted", "customer.subscription.paused", "customer.subscription.resumed"):
            return [BillingEvent(identity, "subscription", reference)]
        if kind == "invoice.payment_failed":
            invoice = plain(await self.client.v1.invoices.retrieve_async(reference))
            subscription = object_id(((invoice.get("parent") or {}).get("subscription_details") or {}).get("subscription"))
            return [BillingEvent(identity, "subscription", subscription)] if subscription else []
        if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded", "checkout.session.expired"):
            session = plain(await self.client.v1.checkout.sessions.retrieve_async(reference))
            if kind == "checkout.session.expired" and session.get("status") == "expired":
                return [BillingEvent(identity, "expired", reference)]
            if session.get("mode") != "subscription" or session.get("payment_status") != "paid":
                return []
            invoice = object_id(session.get("invoice"))
            if not invoice and session.get("subscription"):
                current = await self.subscription(object_id(session["subscription"]))
                invoice = object_id(current.get("latest_invoice"))
            return [BillingEvent(identity, "paid", invoice)] if invoice else []
        if kind in ("charge.refunded", "charge.dispute.created"):
            if kind == "charge.refunded":
                charge = plain(await self.client.v1.charges.retrieve_async(reference))
                if charge.get("amount_refunded", 0) <= 0:
                    return []
                payment = object_id(charge.get("payment_intent"))
            else:
                dispute = plain(await self.client.v1.disputes.retrieve_async(reference))
                payment = object_id(dispute.get("payment_intent"))
            if not payment:
                raise HTTPException(409, "Payment review requires reconciliation.")
            invoice = await self.invoice_for_payment(payment)
            return [BillingEvent(identity, "review", invoice, "refund" if kind == "charge.refunded" else "dispute")]
        return []
