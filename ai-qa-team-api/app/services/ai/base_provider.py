from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider_id: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProviderError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class BaseAIProvider(ABC):
    provider_id: str

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def validate_connection(self, model: str | None = None) -> None: ...
