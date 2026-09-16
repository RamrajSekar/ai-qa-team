from app.config import settings
from app.db.connection import db
from app.services.ai.base_provider import LLMRequest, LLMResponse
from app.services.ai.provider_registry import provider_registry
from app.services.secrets.encrypted_mongo import EncryptedMongoSecretStore


class LLMGateway:
    async def generate(self, project_id: str, request: LLMRequest) -> LLMResponse:
        config = await db["ai_configurations"].find_one({"project_id": project_id, "status": "ACTIVE"})
        if not config:
            provider_id, secret, model, provider_config = "openai", settings.openai_api_key, request.model, {}
        elif config["mode"] == "MANAGED":
            provider_id, secret = "openai", settings.openai_api_key
            model, provider_config = config.get("model"), config.get("configuration", {})
        else:
            provider_id = config["provider_id"]
            secret = await EncryptedMongoSecretStore().get(project_id, config["credential_ref"])
            model, provider_config = config.get("model"), config.get("configuration", {})
        if not secret:
            raise RuntimeError("AI provider is not configured")
        return await provider_registry.resolve(provider_id, secret, model, provider_config).generate(request)
