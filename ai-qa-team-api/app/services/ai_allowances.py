"""Server-owned per-mode allowance policy; provider mode never comes from request input."""
from app.config import settings
from app.app_config.plan_limits import PLAN_LIMITS


def configured_limits(plan):
    if plan in ("team", "business"):
        offer = getattr(settings.pricing, plan)
        return {"managed_ai_credits_limit": offer.managed_ai_credits_limit, "byok_ai_requests_limit": offer.byok_ai_requests_limit}
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
    free = PLAN_LIMITS["free"]
    # Display-only offers. Never feed these planned limits into subscriptions.
    offers = {
        "free": {"monthly_usd": 0, "availability": "available", "users_limit": free["team_members_limit"] + 1,
            **{key: free[key] for key in ("projects_limit", "stories_limit", "scenarios_limit", "testcases_limit")},
            **configured_limits("free")},
        "team": {**settings.pricing.team.model_dump(), "availability": "planned"},
        "business": {**settings.pricing.business.model_dump(), "availability": "planned"},
        "enterprise": {"monthly_usd": None, "availability": "planned"},
    }
    return {"catalog_version": 2, "stage": "EXPERIMENTAL", "currency": "USD", "billing_enabled": False,
        "offers": offers, "contact_url": str(settings.pricing.contact_url) if settings.pricing.contact_url else None,
        "add_ons": {"availability": "planned", "additional_user_monthly_usd": settings.pricing.additional_user_monthly_usd,
            "managed_pack": {"requests": settings.pricing.ai_pack_requests, "usd": settings.pricing.managed_pack_usd},
            "byok_pack": {"requests": settings.pricing.ai_pack_requests, "usd": settings.pricing.byok_pack_usd}},
        # Compatibility catalogue for deployed clients; no existing plan mapping changes.
        "free": {"plan": "free", "monthly_usd": 0, "additional_members_limit": PLAN_LIMITS["free"]["team_members_limit"], **configured_limits("free")},
        "managed": {"plan": "pro", "monthly_usd": settings.pricing.managed_monthly_usd, **configured_limits("pro")},
        "byok": {"plan": "pro", "monthly_usd": settings.pricing.byok_monthly_usd, **configured_limits("pro")},
        "enterprise": {"plan": "enterprise", "monthly_usd": None, **configured_limits("enterprise")},
        "pilot": {"fixed_usd": settings.pricing.pilot_fixed_usd}}
