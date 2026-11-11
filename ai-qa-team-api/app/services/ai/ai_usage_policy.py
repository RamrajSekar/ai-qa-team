from dataclasses import dataclass
from enum import StrEnum

from app.config import settings


class AIOperation(StrEnum):
    BUG_INTERPRETER = "BUG_INTERPRETER"
    KNOWLEDGE_EXTRACTION = "KNOWLEDGE_EXTRACTION"
    STORY_ANALYSIS = "STORY_ANALYSIS"
    SCENARIO_DESIGN = "SCENARIO_DESIGN"
    TEST_DESIGN = "TEST_DESIGN"


@dataclass(frozen=True)
class AIUsagePolicy:
    operation: AIOperation
    monthly_allowance: int | None
    credit_cost: int
    max_input_chars: int
    max_output_tokens: int
    max_concurrent_requests: int
    rate_limit_requests: int
    rate_limit_window_seconds: int
    concurrency_ttl_seconds: int


def get_ai_usage_policy(operation: AIOperation | str) -> AIUsagePolicy:
    try:
        resolved = AIOperation(operation)
    except ValueError as exc:
        raise AIUsageError("AI_OPERATION_UNSUPPORTED", 400, "The AI operation is not supported.") from exc
    config = settings.ai_usage
    return AIUsagePolicy(
        operation=resolved,
        monthly_allowance=None,  # Resolved from subscription.limits.ai_gen_limit.
        credit_cost=config.bug_interpreter_credit_cost if resolved == AIOperation.BUG_INTERPRETER else 1,
        max_input_chars=config.bug_interpreter_max_input_chars if resolved == AIOperation.BUG_INTERPRETER else 70000,
        max_output_tokens=config.bug_interpreter_max_output_tokens if resolved == AIOperation.BUG_INTERPRETER else 6000,
        max_concurrent_requests=config.max_concurrent_requests,
        rate_limit_requests=config.rate_limit_requests,
        rate_limit_window_seconds=config.rate_limit_window_seconds,
        concurrency_ttl_seconds=config.concurrency_ttl_seconds,
    )


class AIUsageError(Exception):
    def __init__(self, code: str, status_code: int, message: str):
        super().__init__(message)
        self.code = code
        self.status_code = status_code

    def public_detail(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}
