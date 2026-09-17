from app.services.ai.base_provider import LLMProviderError


def normalize_provider_error(exc: Exception) -> LLMProviderError:
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    error_type = error.get("type") if isinstance(error, dict) else None
    error_code = error.get("code") if isinstance(error, dict) else None
    error_param = error.get("param") if isinstance(error, dict) else None
    if status in (401, 403) or "authentication" in name or "permission" in name:
        code, message = "AUTHENTICATION_ERROR", "The provider credentials could not be authenticated."
    elif status == 429 or "ratelimit" in name:
        code, message = "RATE_LIMITED", "The AI provider rate limit was reached."
    elif status == 404 or "notfound" in name:
        code, message = "MODEL_NOT_AVAILABLE", "The configured AI model is not available."
    elif "timeout" in name:
        code, message = "TIMEOUT", "The AI provider request timed out."
    elif status is not None and status >= 500:
        code, message = "PROVIDER_UNAVAILABLE", "The AI provider is temporarily unavailable."
    elif status in (400, 422):
        code, message = "PROVIDER_REQUEST_INVALID", "The AI provider rejected the request."
    else:
        code, message = "INVALID_CONFIGURATION", "The provider configuration could not be validated."
    return LLMProviderError(
        code, message, status_code=status,
        provider_error_type=str(error_type) if error_type is not None else None,
        provider_error_code=str(error_code) if error_code is not None else None,
        provider_error_param=str(error_param) if error_param is not None else None,
    )
