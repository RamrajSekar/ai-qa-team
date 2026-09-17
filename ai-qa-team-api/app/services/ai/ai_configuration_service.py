from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.db.connection import db
from app.models.ai_configuration_model import AIConfigurationInput
from app.services.ai.base_provider import LLMProviderError
from app.services.ai.provider_registry import provider_registry
from app.services.secrets.encrypted_mongo import EncryptedMongoSecretStore, SecretStoreConfigurationError


def safe_configuration(document: dict) -> dict:
    return {key: value for key, value in document.items() if key not in {"_id", "credential_ref"}}


async def get_configuration(project_id: str) -> dict | None:
    document = await db["ai_configurations"].find_one({"project_id": project_id})
    return safe_configuration(document) if document else None


async def _resolve_secret(project_id: str, payload: AIConfigurationInput, existing: dict | None = None) -> str:
    if payload.mode == "MANAGED":
        if not settings.openai_api_key: raise HTTPException(503, "Managed AI is not configured")
        return settings.openai_api_key
    if payload.api_key: return payload.api_key
    if existing and existing.get("provider_id") == payload.provider_id and existing.get("credential_ref"):
        return await EncryptedMongoSecretStore().get(project_id, existing["credential_ref"])
    raise HTTPException(422, "API key is required")


def _provider_id(payload: AIConfigurationInput) -> str:
    return "openai" if payload.provider_id == "managed" else payload.provider_id


async def validate_configuration(project_id: str, payload: AIConfigurationInput, existing: dict | None = None) -> None:
    if existing is None:
        existing = await db["ai_configurations"].find_one({"project_id": project_id})
    secret = await _resolve_secret(project_id, payload, existing)
    provider = provider_registry.resolve(_provider_id(payload), secret, payload.model, payload.configuration)
    await provider.validate_connection(payload.model)


async def activate_configuration(project_id: str, payload: AIConfigurationInput, actor: str) -> dict:
    existing = await db["ai_configurations"].find_one({"project_id": project_id})
    old_ref = (existing or {}).get("credential_ref")
    await validate_configuration(project_id, payload, existing)
    now = datetime.now(timezone.utc).isoformat()
    change_type = "PROVIDER_CONFIGURED" if not existing else (
        "PROVIDER_CHANGED" if existing.get("provider_id") != payload.provider_id else
        "CREDENTIAL_REPLACED" if payload.api_key else "CONFIGURATION_UPDATED"
    )
    new_ref = None
    try:
        if payload.mode == "BYOK":
            if payload.api_key:
                new_ref = await EncryptedMongoSecretStore().put(project_id, payload.api_key)
            elif existing and existing.get("provider_id") == payload.provider_id:
                new_ref = existing.get("credential_ref")
            if not new_ref: raise HTTPException(422, "API key is required")
        document = {
            "project_id": project_id, "provider_id": payload.provider_id, "mode": payload.mode,
            "model": payload.model, "configuration": payload.configuration, "credential_ref": new_ref,
            "credential_configured": bool(new_ref), "credential_suffix": payload.api_key[-4:] if payload.api_key else (existing or {}).get("credential_suffix"),
            "status": "ACTIVE", "validated_at": now, "updated_by": actor, "updated_at": now,
            "created_by": (existing or {}).get("created_by", actor), "created_at": (existing or {}).get("created_at", now),
            "last_change": {"type": change_type, "by": actor, "at": now},
        }
        await db["ai_configurations"].update_one({"project_id": project_id}, {"$set": document}, upsert=True)
    except Exception:
        if new_ref and new_ref != (existing or {}).get("credential_ref"):
            await EncryptedMongoSecretStore().delete(project_id, new_ref)
        raise
    if old_ref and old_ref != new_ref:
        try:
            await EncryptedMongoSecretStore().delete(project_id, old_ref)
        except Exception:
            # Activation already succeeded; leave a stale encrypted envelope for cleanup.
            pass
    return safe_configuration(document)


async def remove_configuration(project_id: str) -> None:
    existing = await db["ai_configurations"].find_one({"project_id": project_id})
    await db["ai_configurations"].delete_one({"project_id": project_id})
    if existing and existing.get("credential_ref"):
        await EncryptedMongoSecretStore().delete(project_id, existing["credential_ref"])


def public_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LLMProviderError):
        status_by_code = {
            "AUTHENTICATION_ERROR": 400,
            "MODEL_NOT_AVAILABLE": 400,
            "INVALID_CONFIGURATION": 400,
            "PROVIDER_REQUEST_INVALID": 400,
            "RATE_LIMITED": 429,
            "PROVIDER_UNAVAILABLE": 503,
            "TIMEOUT": 504,
        }
        return HTTPException(status_by_code.get(exc.code, 502), {"code": exc.code, "message": str(exc)})
    if isinstance(exc, SecretStoreConfigurationError): return HTTPException(503, str(exc))
    if isinstance(exc, HTTPException): return exc
    return HTTPException(500, {"code": "PROVIDER_VALIDATION_FAILED", "message": "The provider connection could not be validated."})
