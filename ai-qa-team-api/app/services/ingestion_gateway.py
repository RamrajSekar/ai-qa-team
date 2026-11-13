"""Bounded ingestion tasks through the existing usage boundary; no provider fallback."""
import base64
from dataclasses import replace

from app.config import settings
from app.services.ai.base_provider import LLMResponse, LLMProviderError, normalized_token_usage
from app.services.ai.llm_gateway import LLMGateway
from app.services.ai.provider_errors import normalize_provider_error


class IngestionGateway:
    def __init__(self, payload):
        self.payload = payload

    async def resolve(self, project, request):
        context = await LLMGateway().resolve(project, request)
        if context.provider_id != "openai" or not hasattr(context.provider, "client"):
            raise LLMProviderError("MEDIA_PROVIDER_UNSUPPORTED", "This ingestion task supports the configured OpenAI provider only; no fallback was used.")
        return replace(context, model=context.model or context.provider.default_model)

    async def generate_resolved(self, context, request):
        client = context.provider.client.with_options(timeout=90, max_retries=0)
        try:
            result = await client.chat.completions.create(model=context.model, temperature=0, max_tokens=min(request.max_tokens or 1000,1000),
                messages=[{"role":"system","content":request.system_prompt or ""}, {"role":"user","content":[{"type":"text","text":request.prompt},
                    {"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(self.payload).decode(),"detail":"low"}}]}])
            counts = normalized_token_usage(result)
            return LLMResponse(text=result.choices[0].message.content or "", provider_id=context.provider_id, model=context.model,
                input_tokens=counts[0],output_tokens=counts[1],total_tokens=counts[2])
        except LLMProviderError: raise
        except Exception as failure:
            raise normalize_provider_error(failure) from None
        finally:
            await client.close()
