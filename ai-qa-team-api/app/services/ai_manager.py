from app.services.ai.base_provider import LLMRequest
from app.services.ai.llm_gateway import LLMGateway


class AIManager:
    """Compatibility facade; new AI features should inject LLMGateway directly."""

    def __init__(self, project_id: str, gateway: LLMGateway | None = None):
        self.project_id = project_id
        self.gateway = gateway or LLMGateway()

    async def generate(self, prompt: str) -> str:
        return (await self.gateway.generate(self.project_id, LLMRequest(prompt=prompt))).text
