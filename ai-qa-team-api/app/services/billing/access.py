from datetime import datetime, timezone
from fastapi import HTTPException


def consumption_allowed(account, *, now=None):
    subscription, billing = account.get("subscription", {}), account.get("billing", {})
    if subscription.get("plan") == "free" or not billing.get("managed_spend_required"):
        return True
    now = now or datetime.now(timezone.utc)
    until = billing.get("paid_until")
    return bool(billing.get("status") != "review_required" and isinstance(until, int)
        and not isinstance(until, bool) and until > int(now.timestamp()))


def require_consumption(account, *, now=None):
    if not consumption_allowed(account, now=now):
        raise HTTPException(403, "Billing needs attention. Existing records and manual review remain available.")
