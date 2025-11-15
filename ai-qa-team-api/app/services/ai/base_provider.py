# app/services/ai/base_provider.py

class BaseAIProvider:
    """Base interface for all AI providers."""

    async def generate(self, prompt: str) -> str:
        """Return raw LLM text output."""
        raise NotImplementedError
