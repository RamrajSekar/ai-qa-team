import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import httpx
from pydantic import ValidationError
from app.models.ai_configuration_model import AIConfigurationInput
from app.services.ai.additional_providers import AnthropicProvider, GeminiProvider
from app.services.ai.base_provider import LLMRequest, LLMProviderError
from app.services.ai.provider_catalog import public_provider_catalog


class AdditionalProviderTests(unittest.IsolatedAsyncioTestCase):
    def test_catalog_and_validation(self):
        catalog = {item['provider_id']: item for item in public_provider_catalog()}
        for name in ('gemini', 'anthropic'):
            self.assertEqual(catalog[name]['modes'], ['BYOK'])
            AIConfigurationInput(provider_id=name, mode='BYOK', model='customer-model', api_key='test-key')
            with self.assertRaises(ValidationError):
                AIConfigurationInput(provider_id=name, mode='MANAGED', model='model')
            with self.assertRaises(ValidationError):
                AIConfigurationInput(provider_id=name, mode='BYOK')

    async def test_gemini_fixed_endpoint_schema_and_usage(self):
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))], usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3, total_tokens=13))))))
        client.with_options = lambda **kwargs: client
        with patch('app.services.ai.additional_providers.AsyncOpenAI', return_value=client) as factory:
            provider = GeminiProvider('test-secret', 'customer-model')
            result = await provider.generate(LLMRequest(prompt='data', response_schema={'type':'object','properties':{}} , max_retries=0))
        self.assertEqual(factory.call_args.kwargs['base_url'], 'https://generativelanguage.googleapis.com/v1beta/openai/')
        self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
        self.assertEqual(result.provider_id, 'gemini')
        self.assertEqual(result.total_tokens, 13)
        self.assertEqual(client.chat.completions.create.call_args.kwargs['response_format']['type'], 'json_schema')

    async def test_claude_native_schema_and_usage(self):
        result = {'stop_reason':'end_turn', 'content':[{'type':'text','text':'{}'}], 'usage':{'input_tokens':10,'output_tokens':4}}
        response = httpx.Response(200, json=result, request=httpx.Request('POST', 'https://api.anthropic.com/v1/messages'))
        client = AsyncMock(); client.post.return_value = response
        with patch('app.services.ai.additional_providers.httpx.AsyncClient') as factory:
            factory.return_value.__aenter__.return_value = client
            output = await AnthropicProvider('test-secret','customer-model').generate(LLMRequest(prompt='data',system_prompt='trusted',response_schema={'type':'object','properties':{}}))
        self.assertEqual(output.total_tokens,14)
        self.assertEqual(client.post.await_count,1)
        self.assertEqual(client.post.call_args.args[0], 'https://api.anthropic.com/v1/messages')
        self.assertEqual(client.post.call_args.kwargs['json']['output_config']['format']['type'],'json_schema')
        self.assertEqual(client.post.call_args.kwargs['json']['system'],'trusted')
        self.assertFalse(factory.call_args.kwargs['follow_redirects'])

    async def test_claude_failure_is_sanitized_without_retry(self):
        client = AsyncMock(); client.post.return_value = httpx.Response(401, text='secret should not escape',request=httpx.Request('POST','https://api.anthropic.com/v1/messages'))
        with patch('app.services.ai.additional_providers.httpx.AsyncClient') as factory:
            factory.return_value.__aenter__.return_value = client
            with self.assertRaises(LLMProviderError) as error:
                await AnthropicProvider('test-secret','model').validate_connection()
        self.assertEqual(error.exception.code,'AUTHENTICATION_ERROR')
        self.assertNotIn('secret',str(error.exception))
        self.assertEqual(client.post.await_count,1)
