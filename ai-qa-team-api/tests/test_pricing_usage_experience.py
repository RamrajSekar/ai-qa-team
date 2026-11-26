"""Usage presentation is read-only; dismissal is per authenticated identity."""
import unittest
from copy import deepcopy
from datetime import datetime, timezone

from test_account_billing import DB
from app.services.account_usage_experience import usage_experience, AccountUsageExperience
from app.services.billing.access import consumption_allowed


class UsageExperienceTests(unittest.IsolatedAsyncioTestCase):
    def subscription(self):
        return {"plan": "team", "entitlement_version": 2, "status": "active", "ai_allowance_version": 1,
            "ai_usage_period_start": "2026-11-01T00:00:00+00:00",
            "usage": {"managed_ai_credits_used": 400, "byok_ai_requests_used": 500, "team_members_used": 3,
                "stories_used": 150, "testcases_used": 3001},
            "limits": {"managed_ai_credits_limit": 500, "byok_ai_requests_limit": 500, "team_members_limit": 4,
                "stories_limit": 200, "testcases_limit": 3000}}

    def test_thresholds_seats_and_over_capacity_are_consistent_and_pure(self):
        sub = self.subscription(); before = deepcopy(sub)
        _, view = usage_experience("ACC_fixture", sub, now=datetime(2026, 11, 26, tzinfo=timezone.utc))
        notices = {row["metric"]: row for row in view["notices"]}
        self.assertEqual(notices["managed_ai_credits"]["threshold"], 80)
        self.assertEqual(notices["byok_ai_requests"]["threshold"], 100)
        self.assertEqual(notices["team_members"]["used"], 4)
        self.assertEqual(notices["team_members"]["limit"], 5)
        self.assertEqual(notices["testcases"]["threshold"], 100)
        self.assertNotIn("stories", notices)
        self.assertEqual(view["seats"], {"included": 5, "extra": 0, "purchasable": False})
        self.assertEqual(sub, before)

    def test_month_projection_never_resets_durable_usage_or_saved_capacity(self):
        sub = self.subscription(); before = deepcopy(sub)
        projected, view = usage_experience("ACC_fixture", sub, now=datetime(2026, 12, 1, tzinfo=timezone.utc))
        self.assertTrue(view["period"]["projected"])
        self.assertEqual(projected["usage"]["managed_ai_credits_used"], 0)
        self.assertEqual(projected["usage"]["testcases_used"], 3001)
        self.assertEqual(sub, before)

    def test_unknown_period_is_not_invented_and_zero_unlimited_do_not_warn(self):
        sub = self.subscription(); sub.pop("ai_usage_period_start")
        sub["limits"].update(stories_limit=None, testcases_limit=0)
        sub["usage"].update(testcases_used=0)
        _, view = usage_experience("ACC_fixture", sub)
        self.assertIsNone(view["period"])
        self.assertNotIn("stories", [row["metric"] for row in view["notices"]])
        self.assertNotIn("testcases", [row["metric"] for row in view["notices"]])

    async def test_dismissal_persists_for_one_user_and_does_not_hide_higher_threshold(self):
        db = DB(); service = AccountUsageExperience(db)
        sub = self.subscription(); sub.pop("ai_usage_period_start")
        account = {"_id": "ACC_fixture", "subscription": sub}; user = {"_id": "USER_fixture"}
        _, first = await service.view(account, user, sub)
        notice = next(row for row in first["notices"] if row["metric"] == "managed_ai_credits")
        self.assertEqual(db["account_usage_notice_dismissals"].docs, [])
        await service.dismiss(account, user, notice["id"])
        await service.dismiss(account, user, notice["id"])
        self.assertEqual(len(db["account_usage_notice_dismissals"].docs), 1)
        _, after = await service.view(account, user, sub)
        self.assertNotIn(notice["id"], [row["id"] for row in after["notices"]])
        _, other = await service.view(account, {"_id": "USER_other"}, sub)
        self.assertIn(notice["id"], [row["id"] for row in other["notices"]])
        sub["usage"]["managed_ai_credits_used"] = 500
        _, exhausted = await service.view(account, user, sub)
        self.assertIn(100, [row["threshold"] for row in exhausted["notices"] if row["metric"] == "managed_ai_credits"])

    def test_paid_expiry_blocks_consumption_but_free_capacity_remains(self):
        now = datetime(2026, 11, 26, tzinfo=timezone.utc)
        row = {"subscription": self.subscription(), "billing": {"managed_spend_required": True, "status": "active", "paid_until": int(now.timestamp()) - 1}}
        self.assertFalse(consumption_allowed(row, now=now))
        row["subscription"]["plan"] = "free"
        self.assertTrue(consumption_allowed(row, now=now))
