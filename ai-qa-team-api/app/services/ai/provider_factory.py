# app/services/ai/provider_factory.py
from app.services.ai.openai_provider import OpenAIProvider
from app.config import settings

def get_ai_provider():
    provider_name = settings.ai_provider.lower()

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI is not configured")
        return OpenAIProvider(settings.openai_api_key)

    # Add Groq, Anthropic, DeepSeek, etc.
    raise ValueError(f"Unknown AI provider: {provider_name}")
