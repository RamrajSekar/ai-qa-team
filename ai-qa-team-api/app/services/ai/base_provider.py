from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int | None = None
    response_schema: dict[str, Any] | None = None
    response_schema_name: str | None = None
    prompt_key: str | None = None
    prompt_version: str | None = None


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
    def __init__(self, code: str, message: str, *, status_code: int | None = None,
                 provider_error_type: str | None = None, provider_error_code: str | None = None,
                 provider_error_param: str | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.provider_error_type = provider_error_type
        self.provider_error_code = provider_error_code
        self.provider_error_param = provider_error_param


def strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a copy compatible with OpenAI strict structured outputs.

    Pydantic uses omitted fields for defaults. Strict structured outputs require
    every property to be listed in ``required``; nullable fields remain optional
    in meaning by accepting JSON null.
    """
    result = deepcopy(schema)

    def normalize(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                properties = node.get("properties", {})
                node["additionalProperties"] = False
                node["required"] = list(properties)
            if node.get("default") is None:
                node.pop("default", None)
            for value in node.values():
                normalize(value)
        elif isinstance(node, list):
            for value in node:
                normalize(value)

    normalize(result)
    return result


class BaseAIProvider(ABC):
    provider_id: str

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def validate_connection(self, model: str | None = None) -> None: ...
