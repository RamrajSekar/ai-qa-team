from collections.abc import Callable

from app.services.ai.base_provider import BaseAIProvider
from app.services.ai.azure_openai_provider import AzureOpenAIProvider
from app.services.ai.openai_provider import OpenAIProvider

ProviderFactory = Callable[[str, str | None, dict], BaseAIProvider]


class ProviderRegistry:
    def __init__(self):
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, provider_id: str, factory: ProviderFactory) -> None:
        self._factories[provider_id] = factory

    def resolve(self, provider_id: str, secret: str, model: str | None, configuration: dict) -> BaseAIProvider:
        if provider_id not in self._factories:
            raise ValueError("Unsupported AI provider")
        return self._factories[provider_id](secret, model, configuration)


provider_registry = ProviderRegistry()
provider_registry.register("openai", lambda secret, model, _: OpenAIProvider(secret, model or "gpt-4o-mini"))
provider_registry.register("azure_openai", lambda secret, _model, config: AzureOpenAIProvider(
    secret, config["endpoint"], config["deployment"], config["api_version"]
))
