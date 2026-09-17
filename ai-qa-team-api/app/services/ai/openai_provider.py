from openai import AsyncOpenAI

from app.services.ai.base_provider import BaseAIProvider, LLMRequest, LLMResponse, normalized_token_usage
from app.services.ai.provider_errors import normalize_provider_error


class OpenAIProvider(BaseAIProvider):
    provider_id = "openai"

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.default_model = default_model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        try:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=request.temperature,
                **({"max_tokens": request.max_tokens} if request.max_tokens else {}),
                **({"response_format": {"type": "json_schema", "json_schema": {
                    "name": request.response_schema_name or "structured_response",
                    "strict": True, "schema": request.response_schema,
                }}} if request.response_schema else {}),
            )
            input_tokens, output_tokens, total_tokens = normalized_token_usage(response)
            return LLMResponse(
                text=response.choices[0].message.content or "", provider_id=self.provider_id, model=model,
                input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens,
            )
        except Exception as exc:
            raise normalize_provider_error(exc) from None

    async def validate_connection(self, model: str | None = None) -> None:
        try:
            await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": "user", "content": "Reply OK"}],
                temperature=0,
                max_tokens=2,
            )
        except Exception as exc:
            raise normalize_provider_error(exc) from None
