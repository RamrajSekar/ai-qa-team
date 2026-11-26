"""Explicit synthetic qualification in a claimable Stripe sandbox, never live mode.

Reads the CLI's private profile without printing credentials or hosted URLs. Creates
synthetic products/customer/payment in that sandbox only; expires checkout and
cancels/refunds the synthetic subscription. No application database is used.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tomllib
import traceback
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(MONGO_URI="mongodb://127.0.0.1:27129", MONGO_DB="qa_stripe_fixture_only",
    REDIS_HOST="127.0.0.1", REDIS_PORT="6399", REDIS_USERNAME="", REDIS_PASSWORD="",
    JWT_SECRET_KEY="local-stripe-fixture-only", SESSION_SECRET_KEY="local-stripe-fixture-only")
import stripe
from app.config import settings, BillingSettings
from app.services.billing.stripe_provider import StripeProvider, API_VERSION, plain


async def verify(profile):
    private = tomllib.loads(profile.read_text(encoding="utf-8"))["default"]
    key = private["test_mode_api_key"]
    assert private.get("sandbox_claim_url") and "_test_" in key and "_live_" not in key
    client = stripe.StripeClient(key, stripe_version=API_VERSION, http_client=stripe.HTTPXClient(timeout=20), max_network_retries=0)
    provider = StripeProvider(client=client)
    checks = []
    identity = uuid4().hex
    config = BillingSettings(stripe_key=key, app_origin="http://localhost:3128", mode="test")
    subscription = session = invoice = None
    with patch.object(settings, "billing", config):
        try:
            product = await client.v1.products.create_async({"name": "AI QA Team synthetic billing qualification", "metadata": {"fixture": identity}})
            assert not product.livemode
            price = await client.v1.prices.create_async({"product": product.id, "unit_amount": 4900, "currency": "usd",
                "recurring": {"interval": "month"}})
            assert (await provider.price(price.id))["unit_amount"] == 4900
            checks.append("real_sandbox_monthly_price_read")
            customer = await provider.create_customer("ACC_synthetic_" + identity, identity)
            assert customer == await provider.create_customer("ACC_synthetic_" + identity, identity)
            checks.append("real_customer_idempotency")
            operation = {"_id": identity, "price_id": price.id, "integration_identifier": "ai-qa-team-" + identity[:8],
                "expires_at": int(datetime.now(timezone.utc).timestamp()) + 3600}
            session = await provider.checkout(operation, customer)
            assert session == await provider.checkout(operation, customer)
            checks.append("real_hosted_checkout_creation_and_idempotency")
            configuration = await client.v1.billing_portal.configurations.create_async({"business_profile": {"headline": "Synthetic billing qualification"},
                "features": {"subscription_update": {"enabled": False}, "subscription_cancel": {"enabled": True, "mode": "at_period_end"},
                    "invoice_history": {"enabled": True}, "payment_method_update": {"enabled": True}}})
            config.stripe_portal_configuration = configuration.id
            assert (await provider.portal(customer)).startswith("https://billing.stripe.com/")
            checks.append("real_portal_cancellation_policy_and_hosted_session")
            payment = await client.v1.payment_methods.create_async({"type": "card", "card": {"token": "tok_visa"}})
            await client.v1.payment_methods.attach_async(payment.id, {"customer": customer})
            subscription = await client.v1.subscriptions.create_async({"customer": customer, "items": [{"price": price.id}],
                "default_payment_method": payment.id, "payment_behavior": "error_if_incomplete"})
            assert not subscription.livemode and subscription.status == "active"
            invoice = await provider.paid_invoice(subscription.latest_invoice)
            assert invoice.current and invoice.amount_paid == 4900 and invoice.price_id == price.id and not invoice.livemode
            checks.append("real_test_card_invoice_and_current_api_normalization")
            await client.v1.subscriptions.update_async(subscription.id, {"cancel_at_period_end": True})
            assert (await provider.subscription(subscription.id))["cancel_at_period_end"]
            checks.append("real_period_end_cancellation_read")
            payments = plain(await client.v1.invoice_payments.list_async({"invoice": invoice.invoice_id, "limit": 2}))
            intent = payments["data"][0]["payment"]["payment_intent"]
            assert await provider.invoice_for_payment(intent) == invoice.invoice_id
            refund = await client.v1.refunds.create_async({"payment_intent": intent})
            assert refund.status == "succeeded"  # The already-verified sandbox invoice owns this payment.
            checks.append("real_sandbox_refund_and_payment_to_invoice_mapping")
        finally:
            if session: await client.v1.checkout.sessions.expire_async(session["id"])
            if subscription: await client.v1.subscriptions.cancel_async(subscription.id)
    return {"passed": len(checks), "checks": checks, "live_payments": False,
        "limitations": ["Separate temporary claimable sandbox, not the user's Stripe account", "Hosted checkout was created, not completed in a browser", "No delivered webhook or real AI call qualified"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--private-profile", type=Path, required=True)
    parser.add_argument("--confirm-synthetic-sandbox", action="store_true", required=True); args = parser.parse_args()
    try: print(json.dumps(asyncio.run(verify(args.private_profile)), indent=2))
    except Exception as error:
        # Provider error text/URLs/request bodies can contain credentials or capabilities.
        print(json.dumps({"passed": False, "error_type": type(error).__name__, "provider_code": getattr(error, "code", None),
            "locations": [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name} for frame in traceback.extract_tb(error.__traceback__)]}))
        raise SystemExit(1)
