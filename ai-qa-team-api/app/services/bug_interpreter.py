import json

from pydantic import ValidationError

from app.models.test_intent_model import BugInterpretResponse, InterpretationMetadata, TestIntentV1
from app.services.ai.ai_usage_policy import AIOperation, AIUsageError
from app.services.ai.ai_usage_service import AIUsageService
from app.services.ai.base_provider import LLMProviderError, LLMRequest
from app.services.prompt_defaults import BUG_INTERPRETER_KEY
from app.services.prompt_registry_service import get_active


class BugInterpretationError(Exception):
    def __init__(self, code: str, status_code: int, message: str):
        super().__init__(message)
        self.code = code
        self.status_code = status_code

    def public_detail(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class BugInterpreter:
    def __init__(self, usage_service: AIUsageService | None = None):
        self.usage_service = usage_service or AIUsageService()

    async def interpret(self, project_id: str, user: dict, bug_text: str) -> BugInterpretResponse:
        bug_text = bug_text.strip()
        if not bug_text:
            raise BugInterpretationError("BUG_TEXT_REQUIRED", 422, "Bug text is required.")

        prompt = await get_active(BUG_INTERPRETER_KEY)
        request = LLMRequest(
            system_prompt=prompt["system_prompt"],
            prompt=bug_text,
            temperature=0,
            response_schema=TestIntentV1.model_json_schema(),
            response_schema_name="test_intent_v1",
        )
        try:
            response = await self.usage_service.execute(
                operation=AIOperation.BUG_INTERPRETER,
                project_id=project_id,
                user=user,
                request=request,
            )
        except AIUsageError as exc:
            raise BugInterpretationError(exc.code, exc.status_code, str(exc)) from None
        except LLMProviderError as exc:
            status_by_code = {"AUTHENTICATION_ERROR": 400, "RATE_LIMITED": 429, "TIMEOUT": 504, "PROVIDER_UNAVAILABLE": 503}
            raise BugInterpretationError(exc.code, status_by_code.get(exc.code, 502), str(exc)) from None
        except Exception:
            raise BugInterpretationError("BUG_INTERPRETATION_FAILED", 500, "The bug could not be interpreted.") from None

        try:
            payload = json.loads(response.text)
            if not isinstance(payload, dict):
                raise ValueError("Structured response must be an object")
            # Source and version are application-owned contract identity.
            payload["source"] = "PASTED_BUG"
            payload["schema_version"] = "1"
            test_intent = TestIntentV1.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError):
            raise BugInterpretationError(
                "INVALID_TEST_INTENT", 422,
                "The AI response did not satisfy the TestIntentV1 contract.",
            ) from None

        return BugInterpretResponse(
            test_intent=test_intent,
            interpretation_metadata=InterpretationMetadata(
                prompt_key=prompt["prompt_key"],
                prompt_version=prompt["resolved_version"],
                prompt_source=prompt["source"],
            ),
        )
