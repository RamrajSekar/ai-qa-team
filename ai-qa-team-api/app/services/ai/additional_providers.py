"""Fixed-endpoint BYOK adapters; credentials never select an arbitrary host."""
import httpx
from openai import AsyncOpenAI

from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.base_provider import BaseAIProvider, LLMRequest, LLMResponse, LLMProviderError, strict_json_schema
from app.services.ai.provider_errors import normalize_provider_error


class GeminiProvider(OpenAIProvider):
    provider_id = "gemini"

    def __init__(self, api_key: str, model: str):
        self.default_model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/", max_retries=0)


class AnthropicProvider(BaseAIProvider):
    provider_id = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.default_model = model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        body = {"model": model, "max_tokens": request.max_tokens or 4096,
                "messages": [{"role": "user", "content": request.prompt}]}
        if request.system_prompt:
            body["system"] = request.system_prompt
        if request.response_schema:
            body["output_config"] = {"format": {"type": "json_schema", "schema": strict_json_schema(request.response_schema)}}
        try:
            # No automatic retries after ambiguous responses or redirects to other hosts.
            async with httpx.AsyncClient(timeout=90, follow_redirects=False) as client:
                response = await client.post("https://api.anthropic.com/v1/messages", json=body,
                    headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"})
                response.raise_for_status()
                result = response.json()
        except httpx.HTTPStatusError as exc:
            safe_error = Exception()
            safe_error.status_code = exc.response.status_code
            raise normalize_provider_error(safe_error) from None
        except Exception as exc:
            raise normalize_provider_error(exc) from None
        if result.get("stop_reason") != "end_turn":
            raise LLMProviderError("PROVIDER_REQUEST_INVALID", "The provider did not complete the response. Review the model and output limit.")
        usage = result.get("usage", {})
        input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        return LLMResponse(text="".join(block.get("text", "") for block in result.get("content", []) if block.get("type") == "text"),
            provider_id=self.provider_id, model=model, input_tokens=input_tokens, output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens if isinstance(input_tokens, int) and isinstance(output_tokens, int) else None)

    async def validate_connection(self, model: str | None = None) -> None:
        await self.generate(LLMRequest(prompt="Reply OK", model=model, max_tokens=32, max_retries=0))
