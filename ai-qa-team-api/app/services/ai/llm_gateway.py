from dataclasses import dataclass

from app.config import settings
from app.db.connection import db
from app.services.ai.base_provider import BaseAIProvider, LLMRequest, LLMResponse
from app.services.ai.provider_registry import provider_registry
from app.services.secrets.encrypted_mongo import EncryptedMongoSecretStore


@dataclass(frozen=True)
class ResolvedLLMContext:
    mode: str
    provider_id: str
    model: str | None
    provider: BaseAIProvider


class LLMGateway:
    async def resolve(self, project_id: str, request: LLMRequest) -> ResolvedLLMContext:
        config = await db["ai_configurations"].find_one({"project_id": project_id, "status": "ACTIVE"})
        if not config:
            mode, provider_id, secret, model, provider_config = "MANAGED", "openai", settings.openai_api_key, request.model, {}
        elif config["mode"] == "MANAGED":
            mode, provider_id, secret = "MANAGED", "openai", settings.openai_api_key
            model, provider_config = config.get("model"), config.get("configuration", {})
        else:
            mode, provider_id = "BYOK", config["provider_id"]
            secret = await EncryptedMongoSecretStore().get(project_id, config["credential_ref"])
            model, provider_config = config.get("model"), config.get("configuration", {})
        if not secret:
            raise RuntimeError("AI provider is not configured")
        provider = provider_registry.resolve(provider_id, secret, model, provider_config)
        return ResolvedLLMContext(mode=mode, provider_id=provider_id, model=model or request.model, provider=provider)

    async def generate_resolved(self, context: ResolvedLLMContext, request: LLMRequest) -> LLMResponse:
        return await context.provider.generate(request)

    async def generate(self, project_id: str, request: LLMRequest) -> LLMResponse:
        context = await self.resolve(project_id, request)
        return await self.generate_resolved(context, request)
