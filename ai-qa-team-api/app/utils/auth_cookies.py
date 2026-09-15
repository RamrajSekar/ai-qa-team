from datetime import datetime, timedelta, timezone

from fastapi import Response

from app.config import settings
from app.utils.jwt_handler import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)


ACCESS_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _cookie_options(max_age: int) -> dict:
    return {
        "httponly": True,
        "secure": settings.app_env.strip().lower() == "production",
        "samesite": "lax",
        "path": "/",
        "max_age": max_age,
        "expires": datetime.now(timezone.utc) + timedelta(seconds=max_age),
    }


def set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        **_cookie_options(ACCESS_COOKIE_MAX_AGE),
    )


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        **_cookie_options(REFRESH_COOKIE_MAX_AGE),
    )


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)


def clear_auth_cookies(response: Response) -> None:
    options = {
        "httponly": True,
        "secure": settings.app_env.strip().lower() == "production",
        "samesite": "lax",
        "path": "/",
    }
    response.delete_cookie(key="access_token", **options)
    response.delete_cookie(key="refresh_token", **options)
