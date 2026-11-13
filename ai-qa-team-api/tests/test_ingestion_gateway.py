"""SDK/provider capability doubles only; no image requests are sent."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from app.services.ingestion_gateway import IngestionGateway
from app.services.ai.llm_gateway import ResolvedLLMContext
from app.services.ai.base_provider import LLMRequest, LLMProviderError


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def context(self):
        self.clone=SimpleNamespace(close=AsyncMock(),chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='Observed synthetic image.'))],usage=SimpleNamespace(prompt_tokens=10,completion_tokens=2,total_tokens=12))))))
        self.provider=SimpleNamespace(client=SimpleNamespace(with_options=Mock(return_value=self.clone)),default_model='gpt-4o-mini')
        return ResolvedLLMContext(mode='BYOK',provider_id='openai',model=None,provider=self.provider)

    async def test_images_use_inline_bounded_observations_and_model_usage(self):
        context=self.context();gateway=IngestionGateway(b'synthetic png');request=LLMRequest(prompt='Observe only',max_tokens=1000)
        with patch('app.services.ingestion_gateway.LLMGateway.resolve',new=AsyncMock(return_value=context)):
            resolved=await gateway.resolve('P1',request)
        result=await gateway.generate_resolved(resolved,request)
        self.assertEqual(resolved.mode,'BYOK')
        self.assertEqual(self.provider.client.with_options.call_args.kwargs['max_retries'],0)
        arguments=self.clone.chat.completions.create.call_args.kwargs
        self.assertEqual(arguments['model'],'gpt-4o-mini');self.assertEqual(result.total_tokens,12)
        self.assertTrue(arguments['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))

    async def test_unsupported_provider_does_not_fall_back_to_platform_account(self):
        context=ResolvedLLMContext(mode='BYOK',provider_id='azure_openai',model='deployment',provider=SimpleNamespace())
        with patch('app.services.ingestion_gateway.LLMGateway.resolve',new=AsyncMock(return_value=context)):
            with self.assertRaises(LLMProviderError) as failure:await IngestionGateway(b'a').resolve('P1',LLMRequest(prompt='test'))
        self.assertEqual(failure.exception.code,'MEDIA_PROVIDER_UNSUPPORTED')
