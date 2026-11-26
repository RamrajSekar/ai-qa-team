"""Read-only usage projection; only explicit dismissal writes a user-scoped receipt."""
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import HTTPException
from app.services.resource_quota import fingerprint


def month(now):
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    end = datetime(now.year + (now.month == 12), 1 if now.month == 12 else now.month + 1, 1, tzinfo=timezone.utc)
    return start, end


def date(value):
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, AttributeError):
        return None


def usage_experience(account_id, subscription, *, now=None):
    now = now or datetime.now(timezone.utc)
    sub = deepcopy(subscription)
    usage, limits = sub.get("usage", {}), sub.get("limits", {})
    start, end = month(now)
    stored = date(sub.get("ai_usage_period_start"))
    projected = stored is not None and stored < start
    valid_period = stored is not None and stored <= start
    if projected:
        for key in ("ai_gen_used", "managed_ai_credits_used", "byok_ai_requests_used"):
            usage[key] = 0
    period = {"start": start.isoformat(), "end": end.isoformat(), "timezone": "UTC", "projected": projected} if valid_period else None
    notices = []
    pools = (("managed_ai_credits", "Managed AI", True), ("byok_ai_requests", "BYOK AI", True)) if sub.get("ai_allowance_version") == 1 else (("ai_gen", "AI requests", True),)
    for metric, label, ai in (("projects", "Projects", False), ("stories", "Stories", False),
            ("scenarios", "Scenarios", False), ("testcases", "Test cases", False), ("team_members", "Users", False), *pools):
        used, limit = usage.get(metric + "_used"), limits.get(metric + "_limit")
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (used, limit)):
            continue
        if metric == "team_members":
            used += 1
            limit += 1
        if limit == 0 and used == 0 or limit > 0 and used * 100 < limit * 80:
            continue
        threshold = 100 if used >= limit else 80
        policy = start.isoformat() if ai and valid_period else fingerprint([sub.get("plan"), sub.get("entitlement_version"), limit])
        identity = fingerprint([account_id, metric, policy, threshold])
        message = (f"{label} limit reached. " + ("Manual work stays available." if ai else "Existing records stay available.")) if threshold == 100 else f"{label}: at least 80% used."
        notices.append({"id": identity, "metric": metric, "threshold": threshold, "message": message, "used": used, "limit": limit})
    members_limit = limits.get("team_members_limit")
    seats = {"included": members_limit + 1 if isinstance(members_limit, int) and not isinstance(members_limit, bool) else None,
        "extra": 0, "purchasable": False}
    return sub, {"period": period, "seats": seats, "notices": notices}


class AccountUsageExperience:
    def __init__(self, database):
        self.db = database

    @staticmethod
    def identity(user):
        return str(user.get("_id") or user.get("id") or user["email"])

    async def view(self, account, user, subscription):
        sub, experience = usage_experience(account["_id"], subscription)
        from app.services.billing.access import consumption_allowed
        experience["billing_attention"] = not consumption_allowed(account)
        identifiers = [notice["id"] for notice in experience["notices"]]
        if identifiers:
            rows = await self.db["account_usage_notice_dismissals"].find({"account_id": account["_id"],
                "user_id": self.identity(user), "notice_id": {"$in": identifiers}}, {"notice_id": 1}).to_list(32)
            dismissed = {row["notice_id"] for row in rows}
            experience["notices"] = [notice for notice in experience["notices"] if notice["id"] not in dismissed]
        return sub, experience

    async def dismiss(self, account, user, notice_id):
        _, experience = usage_experience(account["_id"], account["subscription"])
        if notice_id not in {notice["id"] for notice in experience["notices"]}:
            raise HTTPException(404, "Usage notice is no longer available in this account.")
        identity = fingerprint([account["_id"], self.identity(user), notice_id])
        await self.db["account_usage_notice_dismissals"].update_one({"_id": identity}, {"$setOnInsert": {
            "account_id": account["_id"], "user_id": self.identity(user), "notice_id": notice_id,
            "dismissed_at": datetime.now(timezone.utc)}}, upsert=True)
