from urllib.parse import urlsplit
from fastapi import HTTPException
from app.config import settings


def require_configuration(*, live=False):
    config = settings.billing
    key = config.stripe_key.get_secret_value() if config.stripe_key else ""
    origin = urlsplit(str(config.app_origin or ""))
    local = origin.hostname in ("localhost", "127.0.0.1") and settings.app_env.lower() in ("local", "test", "development")
    if (not settings.features.billing_checkout or not settings.features.customer_accounts or not settings.features.account_subscriptions
            or not settings.features.separate_ai_allowances or not config.stripe_webhook_secret or not key
            or f"_{config.mode}_" not in key or not origin.netloc or origin.username or origin.password or origin.query or origin.fragment
            or origin.scheme != "https" and not (origin.scheme == "http" and local)
            or any(not config.stripe_price_ids.get(plan, "").startswith("price_") for plan in ("team", "business"))):
        raise HTTPException(503, "Billing is not configured for purchasing.")
    spend = settings.managed_spend
    if (not settings.features.managed_spend_guard or not spend.cutover_id or not spend.rates_verified
            or not spend.models or not spend.pricing_revision or spend.per_request_micro_usd <= 0
            or spend.platform_monthly_micro_usd <= 0
            or any(spend.account_monthly_micro_usd.get(plan, 0) <= 0 for plan in ("free", "team", "business"))):
        raise HTTPException(503, "Managed AI spend safeguards must be configured before purchasing.")
    if config.mode == "live" or live:
        if (config.mode != "live" or not all((config.live_mode_approved, config.commercial_terms_reviewed,
                config.tax_setup_verified, config.sandbox_qualified, config.terms_url, config.privacy_url,
                config.stripe_portal_configuration))
                or any(urlsplit(str(url)).scheme != "https" or urlsplit(str(url)).username or urlsplit(str(url)).password
                    for url in (config.terms_url, config.privacy_url))):
            raise HTTPException(503, "Live purchasing has not been approved.")
    from app.services.ai.managed_spend import qualified_model
    from app.services.ai.ai_usage_policy import AIUsageError
    try:
        qualified_model("gpt-4o-mini", 6000)
    except AIUsageError:
        raise HTTPException(503, "The default Managed model requires a qualified spend profile.") from None
    return config


def public_checkout_enabled():
    try:
        require_configuration(live=True)
        return True
    except HTTPException:
        return False
