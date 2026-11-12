"""Optional email and Free allowance tests. No network or external email delivery."""
from copy import deepcopy
import ssl
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from pydantic import SecretStr
import test_account_billing as fixtures
from test_account_billing import settings, CustomerAccounts
from app.services import invitation_email
from app.services.free_member_allowance import plan_free_allowance, apply_free_allowance
from app.models.subscription import Subscription


class InvitationEmailTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.AccountBillingTests.setUp
    client = fixtures.AccountBillingTests.client

    def configured(self):
        from contextlib import ExitStack
        stack = ExitStack(); self.addCleanup(stack.close)
        for target, key, value in [(settings.features, "account_invitation_email", True), (settings, "smtp_host", "smtp.example.com"),
            (settings, "smtp_username", "synthetic"), (settings, "smtp_password", SecretStr("synthetic-mail-password")),
            (settings, "smtp_from_email", "invitations@example.com"), (settings, "frontend_url", "http://localhost:3000")]:
            stack.enter_context(patch.object(target, key, value))

    async def test_manual_link_remains_default_without_email_configuration(self):
        with patch.object(invitation_email, "send_invitation", new=AsyncMock()) as sender:
            response = self.client(self.owner).post('/account/invitations', json={"email": "link@example.com"})
        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.json()); sender.assert_not_awaited()

    async def test_email_requires_feature_and_configuration_before_creating_invitation(self):
        client = self.client(self.owner)
        request = {"email": "email@example.com", "delivery": "EMAIL"}
        self.assertEqual(client.post('/account/invitations', json=request).status_code, 403)
        settings.features.account_invitation_email = True
        with patch.object(settings, "smtp_host", None):
            self.assertEqual(client.post('/account/invitations', json=request).status_code, 503)
        self.assertEqual(self.db["account_invitations"].docs, [])
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["team_members_used"], 0)

    async def test_configured_email_delivery_hides_token_and_keeps_hashed_invitation(self):
        self.configured()
        with patch.object(invitation_email, "send_invitation", new=AsyncMock()) as sender:
            response = self.client(self.owner).post('/account/invitations', json={"email": "email@example.com", "delivery": "EMAIL"})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("token", response.json())
        self.assertEqual(response.json()["email_delivery"], "SENT")
        sender.assert_awaited_once()
        token = sender.await_args.args[1]
        self.assertNotIn(token, str(self.db["account_invitations"].docs))

    async def test_uncertain_email_retains_seat_and_does_not_resend_or_reveal_error(self):
        self.configured(); client = self.client(self.owner)
        request = {"email": "uncertain@example.com", "delivery": "EMAIL"}
        with patch.object(invitation_email, "send_invitation", new=AsyncMock(side_effect=TimeoutError("synthetic-private-transport-error"))) as sender:
            response = client.post('/account/invitations', json=request)
            self.assertEqual(response.status_code, 502)
            self.assertNotIn("synthetic-private", response.text)
            self.assertEqual(client.post('/account/invitations', json=request).status_code, 409)
            sender.assert_awaited_once()
        self.assertEqual(self.db["account_invitations"].docs[0]["email_delivery"], "UNKNOWN")
        self.assertEqual(self.db["customer_accounts"].docs[0]["subscription"]["usage"]["team_members_used"], 1)

    async def test_member_cannot_send_and_smtp_transport_requires_verified_tls(self):
        self.configured()
        with patch.object(invitation_email, "send_invitation", new=AsyncMock()) as sender:
            self.assertEqual(self.client(self.member).post('/account/invitations', json={"email": "no@example.com", "delivery": "EMAIL"}).status_code, 403)
            sender.assert_not_awaited()
        smtp = MagicMock(); connection = smtp.__enter__.return_value
        with patch.object(invitation_email.smtplib, "SMTP", return_value=smtp) as factory, patch.object(settings, "smtp_port", 587):
            invitation_email._send("synthetic@example.com", "synthetic-token", "Synthetic Customer")
        factory.assert_called_once_with("smtp.example.com", 587, timeout=10)
        context = connection.starttls.call_args.kwargs["context"]
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        message = connection.send_message.call_args.args[0]
        self.assertIn('/auth?mode=signup#invite=synthetic-token', message.get_content())
        self.assertNotIn('synthetic-mail-password', message.get_content())

    async def test_free_allowance_update_preserves_usage_and_custom_or_paid_limits(self):
        model = Subscription(); model.apply_plan_defaults()
        self.assertEqual(model.limits.team_members_limit, 2)
        records = self.db["customer_accounts"].docs
        records[0]["subscription"]["limits"]["team_members_limit"] = 1
        records[1]["subscription"]["plan"] = "pro"
        records[1]["subscription"]["limits"]["team_members_limit"] = 1
        before = deepcopy(records)
        plan = plan_free_allowance(records)
        self.assertEqual(len(plan["changes"]), 1)
        with self.assertRaises(ValueError): await apply_free_allowance(self.db, plan, "wrong")
        await apply_free_allowance(self.db, plan, plan["plan_digest"])
        self.assertEqual(records[0]["subscription"]["limits"]["team_members_limit"], 2)
        self.assertEqual(records[0]["subscription"]["usage"], before[0]["subscription"]["usage"])
        self.assertEqual(records[1], before[1])
        self.assertEqual(plan_free_allowance(records)["changes"], [])


if __name__ == "__main__": unittest.main()
