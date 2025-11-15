# app/services/ai/provider_factory.py
from app.services.ai.openai_provider import OpenAIProvider
from app.config import settings

def get_ai_provider():
    provider_name = settings.ai_provider.lower()

    if provider_name == "openai":
        return OpenAIProvider()

    # Add Groq, Anthropic, DeepSeek, etc.
    raise ValueError(f"Unknown AI provider: {provider_name}")
