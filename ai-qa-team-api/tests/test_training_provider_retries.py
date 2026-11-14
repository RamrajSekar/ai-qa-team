"""Request-scoped retry policy. No SDK network calls or credentials."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from app.services.ai.base_provider import LLMRequest
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.azure_openai_provider import AzureOpenAIProvider


class TrainingProviderRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_training_disables_sdk_retries_without_changing_other_requests(self):
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])
        for provider_type in (OpenAIProvider, AzureOpenAIProvider):
            with self.subTest(provider=provider_type.__name__):
                provider = object.__new__(provider_type)
                provider.default_model = "synthetic"; provider.deployment = "synthetic"
                normal = AsyncMock(return_value=response); bounded = AsyncMock(return_value=response)
                client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=bounded)))
                provider.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=normal)),
                    with_options=Mock(return_value=client))
                await provider.generate(LLMRequest(prompt="synthetic", max_retries=0))
                provider.client.with_options.assert_called_once_with(max_retries=0)
                self.assertEqual(bounded.await_count, 1); self.assertEqual(normal.await_count, 0)
                provider.client.with_options.reset_mock()
                await provider.generate(LLMRequest(prompt="other existing task"))
                provider.client.with_options.assert_not_called(); self.assertEqual(normal.await_count, 1)
