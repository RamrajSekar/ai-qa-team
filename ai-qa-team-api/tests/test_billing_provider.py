"""Provider contracts and signed-envelope rejection; no provider/network calls."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"MONGO_URI": "mongodb://127.0.0.1:27129", "MONGO_DB": "billing_unit_fixture",
    "REDIS_HOST": "127.0.0.1", "REDIS_PORT": "6399", "REDIS_USERNAME": "", "REDIS_PASSWORD": "",
    "JWT_SECRET_KEY": "synthetic-unit-only", "SESSION_SECRET_KEY": "synthetic-unit-only"}):
    from app.config import settings, BillingSettings
    from app.services.billing.stripe_provider import StripeProvider, API_VERSION, hosted_url, plain
    from app.services.ai.managed_spend import qualified_model
    from app.services.ai.ai_usage_policy import AIUsageError
from fastapi import HTTPException
import stripe


class BillingProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = BillingSettings(mode="test", stripe_webhook_secret="whsec_synthetic", app_origin="https://example.com",
            stripe_portal_configuration="bpc_fixture")
        self.config_patch = patch.object(settings, "billing", self.config); self.config_patch.start()
        self.addCleanup(self.config_patch.stop)

    def signed(self, event, timestamp=None):
        body = json.dumps(event).encode(); now = timestamp if timestamp is not None else int(time.time())
        digest = hmac.new(b"whsec_synthetic", str(now).encode() + b"." + body, hashlib.sha256).hexdigest()
        return body, f"t={now},v1={digest}"

    def test_signature_mode_version_tenant_and_staleness(self):
        provider = StripeProvider()
        event = {"id": "evt_fixture", "type": "invoice.paid", "api_version": API_VERSION, "livemode": False,
            "data": {"object": {"id": "in_fixture"}}}
        self.assertEqual(provider.verify_event(*self.signed(event))["id"], "evt_fixture")
        for changed in ({**event, "livemode": True}, {**event, "api_version": "old"}, {**event, "account": "acct_other"}):
            with self.assertRaises(HTTPException): provider.verify_event(*self.signed(changed))
        with self.assertRaises(HTTPException): provider.verify_event(*self.signed(event, int(time.time()) - 600))
        payload, signature = self.signed(event)
        with self.assertRaises(HTTPException): provider.verify_event(payload + b" ", signature)

    def test_sdk17_plain_objects_and_hosted_url_restrictions(self):
        obj = stripe.StripeObject.construct_from({"id": "in_fixture", "lines": {"data": [{"id": "il_fixture"}]}}, None)
        self.assertEqual(plain(obj)["lines"]["data"][0]["id"], "il_fixture")
        for url in ("http://checkout.stripe.com/a", "https://checkout.stripe.com.evil.test/a", "https://a@checkout.stripe.com/a", "https://checkout.stripe.com:8443/a"):
            with self.assertRaises(HTTPException): hosted_url(url, "checkout.stripe.com")

    def test_spend_rejects_invalid_output_bounds(self):
        for value in (0, -1, True, "100", None):
            with self.assertRaises(AIUsageError): qualified_model("gpt-4o-mini", value)

    async def test_checkout_uses_saved_identity_server_price_and_no_payment_method_list(self):
        create = AsyncMock(return_value={"id": "cs_fixture", "livemode": False, "url": "https://checkout.stripe.com/c/pay/fixture"})
        provider = StripeProvider(client=SimpleNamespace(v1=SimpleNamespace(checkout=SimpleNamespace(sessions=SimpleNamespace(create_async=create)))))
        operation = {"_id": "saved", "price_id": "price_saved", "integration_identifier": "ai-qa-team-abcdefgh", "expires_at": 1900000000}
        await provider.checkout(operation, "cus_fixture"); await provider.checkout(operation, "cus_fixture")
        self.assertEqual(create.call_args_list[0], create.call_args_list[1])
        params = create.call_args.args[0]
        self.assertEqual(params["line_items"], [{"price": "price_saved", "quantity": 1}])
        self.assertNotIn("payment_method_types", params)
        self.assertEqual(create.call_args.kwargs["options"]["idempotency_key"], "checkout:saved")

    async def test_portal_requires_period_end_cancellation_and_disabled_plan_changes(self):
        retrieve = AsyncMock(return_value={"active": True, "features": {"subscription_update": {"enabled": False},
            "subscription_cancel": {"enabled": True, "mode": "at_period_end"}}})
        create = AsyncMock(return_value=SimpleNamespace(url="https://billing.stripe.com/p/session/fixture"))
        provider = StripeProvider(client=SimpleNamespace(v1=SimpleNamespace(billing_portal=SimpleNamespace(
            configurations=SimpleNamespace(retrieve_async=retrieve), sessions=SimpleNamespace(create_async=create)))))
        self.assertTrue((await provider.portal("cus_fixture")).startswith("https://billing.stripe.com/"))
        retrieve.return_value["features"]["subscription_cancel"]["enabled"] = False
        with self.assertRaises(HTTPException): await provider.portal("cus_fixture")
        self.assertEqual(create.await_count, 1)

    async def test_paid_invoice_handles_current_api_and_rejects_proration(self):
        invoice = {"status": "paid", "customer": "cus_fixture", "parent": {"subscription_details": {"subscription": "sub_fixture"}},
            "lines": {"data": [{"quantity": 1, "pricing": {"price_details": {"price": "price_fixture"}},
                "parent": {"subscription_item_details": {"proration": False}}, "period": {"end": 1900000000}}]},
            "amount_paid": 4900, "subtotal": 4900, "currency": "usd", "livemode": False, "billing_reason": "subscription_create"}
        retrieve = AsyncMock(return_value=invoice)
        provider = StripeProvider(client=SimpleNamespace(v1=SimpleNamespace(invoices=SimpleNamespace(retrieve_async=retrieve))))
        provider.subscription = AsyncMock(return_value={"latest_invoice": "in_fixture", "status": "active"})
        result = await provider.paid_invoice("in_fixture")
        self.assertTrue(result.current); self.assertEqual(result.price_id, "price_fixture")
        invoice["lines"]["data"][0]["parent"]["subscription_item_details"]["proration"] = True
        with self.assertRaises(HTTPException): await provider.paid_invoice("in_fixture")
        invoice["parent"] = None
        with self.assertRaises(HTTPException): await provider.paid_invoice("in_fixture")

    async def test_raw_webhook_route_rejects_tampering_before_dispatch(self):
        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from app.routes import billing_routes
        provider = StripeProvider()
        provider.normalize_event = AsyncMock(return_value=[])
        app = FastAPI(); app.include_router(billing_routes.router)
        body, signature = self.signed({"id": "evt_fixture", "type": "synthetic.unhandled", "api_version": API_VERSION,
            "livemode": False, "data": {"object": {"id": "obj_fixture"}}})
        with patch.object(billing_routes.billing_providers, "resolve", return_value=provider):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://fixture") as client:
                response = await client.post("/billing/webhooks/stripe", content=body + b" ", headers={"stripe-signature": signature})
                self.assertEqual(response.status_code, 400); provider.normalize_event.assert_not_awaited()
                response = await client.post("/billing/webhooks/stripe", content=body, headers={"stripe-signature": signature})
                self.assertEqual(response.status_code, 200); self.assertEqual(response.json(), {"received": True})
                response = await client.post("/billing/webhooks/unknown", content=body)
                self.assertEqual(response.status_code, 404)


if __name__ == "__main__": unittest.main()
