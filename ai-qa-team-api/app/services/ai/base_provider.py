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
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def normalized_token_usage(response: Any) -> tuple[int | None, int | None, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None, None, None
    def value(*names: str) -> int | None:
        return next((item for name in names if (item := getattr(usage, name, None)) is not None), None)
    return (
        value("prompt_tokens", "input_tokens"),
        value("completion_tokens", "output_tokens"),
        value("total_tokens"),
    )


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
