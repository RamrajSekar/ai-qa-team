"""Shared feature checks for HTTP entry points and execution services."""

from fastapi import HTTPException

from app.config import FeatureFlags, settings


def require_features(*names: str) -> None:
    for name in names:
        if name not in FeatureFlags.model_fields:
            raise ValueError(f"Unknown feature: {name}")
        if not getattr(settings.features, name):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "feature_disabled",
                    "feature": name,
                    "message": f"Feature '{name}' is disabled.",
                },
            )


def feature_required(*names: str):
    """Run before authentication/quota dependencies that may have side effects."""
    async def check_features() -> None:
        require_features(*names)

    return check_features
