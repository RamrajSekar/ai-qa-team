from app.services.ai.base_provider import LLMProviderError


def normalize_provider_error(exc: Exception) -> LLMProviderError:
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None)
    if status in (401, 403) or "authentication" in name or "permission" in name:
        code = "AUTHENTICATION_ERROR"
    elif status == 429 or "ratelimit" in name:
        code = "RATE_LIMITED"
    elif status == 404 or "notfound" in name:
        code = "MODEL_NOT_AVAILABLE"
    elif "timeout" in name:
        code = "TIMEOUT"
    elif status is not None and status >= 500:
        code = "PROVIDER_UNAVAILABLE"
    else:
        code = "INVALID_CONFIGURATION"
    return LLMProviderError(code, "The provider connection could not be validated.")
