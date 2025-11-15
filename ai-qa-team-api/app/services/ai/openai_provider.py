from app.services.ai.base_provider import BaseAIProvider
from openai import AsyncOpenAI
from app.config import settings
import logging
from openai import OpenAIError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """Adapter for OpenAI/ChatGPT"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "Sorry, I couldn't generate a response due to an internal error."
        except Exception as e:
            logger.exception(f"Unexpected error in OpenAIProvider.generate: {e}")
            return "An unexpected error occurred while generating the response."
