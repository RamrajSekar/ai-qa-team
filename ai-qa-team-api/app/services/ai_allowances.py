"""Server-owned per-mode allowance policy; provider mode never comes from request input."""
from app.config import settings
from app.app_config.plan_limits import PLAN_LIMITS


def configured_limits(plan):
    if plan not in {"free", "pro", "enterprise"}:
        raise ValueError("Unsupported plan for AI allowances.")
    return {"managed_ai_credits_limit": getattr(settings.ai_allowances, plan + "_managed"),
            "byok_ai_requests_limit": getattr(settings.ai_allowances, plan + "_byok")}


def initialize_allowances(subscription):
    subscription["ai_allowance_version"] = 1
    subscription.setdefault("limits", {}).update(configured_limits(subscription.get("plan", "free")))
    subscription.setdefault("usage", {}).update({"managed_ai_credits_used": 0, "byok_ai_requests_used": 0})
    return subscription


def public_pricing():
    return {"stage": "EXPERIMENTAL", "currency": "USD", "billing_enabled": False,
        "free": {"plan": "free", "monthly_usd": 0, "additional_members_limit": PLAN_LIMITS["free"]["team_members_limit"], **configured_limits("free")},
        "managed": {"plan": "pro", "monthly_usd": settings.pricing.managed_monthly_usd, **configured_limits("pro")},
        "byok": {"plan": "pro", "monthly_usd": settings.pricing.byok_monthly_usd, **configured_limits("pro")},
        "enterprise": {"plan": "enterprise", "monthly_usd": None, **configured_limits("enterprise")},
        "pilot": {"fixed_usd": settings.pricing.pilot_fixed_usd}}
