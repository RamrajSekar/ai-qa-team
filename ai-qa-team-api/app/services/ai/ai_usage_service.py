import asyncio
import logging
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from pymongo import ReturnDocument

from app.config import settings
from app.db.connection import db
from app.services.ai.ai_usage_policy import AIOperation, AIUsageError, AIUsagePolicy, get_ai_usage_policy
from app.services.ai.base_provider import LLMProviderError, LLMRequest, LLMResponse
from app.services.ai.llm_gateway import LLMGateway, ResolvedLLMContext
from app.utils import redis_client as redis_module


logger = logging.getLogger(__name__)


def _month_period(now: datetime) -> tuple[datetime, datetime]:
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    end = datetime(now.year + (now.month == 12), 1 if now.month == 12 else now.month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _identity(user: dict) -> tuple[str, str]:
    email = str(user.get("email") or "").strip().lower()
    user_id = str(user.get("_id") or user.get("id") or email)
    return email, user_id


class AIUsageService:
    """Server-owned policy, reservation, limiting, invocation, and telemetry boundary."""

    def __init__(self, *, database=None, redis_backend=None, gateway=None, now=None):
        self.db = database if database is not None else db
        self.redis = redis_backend if redis_backend is not None else redis_module.redis_client
        self.gateway = gateway or LLMGateway()
        self.now = now or (lambda: datetime.now(timezone.utc))

    async def execute(self, operation: AIOperation | str, project_id: str, user: dict, request: LLMRequest) -> LLMResponse:
        policy = get_ai_usage_policy(operation)
        if len(request.prompt) > policy.max_input_chars:
            raise AIUsageError("AI_INPUT_TOO_LARGE", 413, "The AI input exceeds the allowed size.")

        project, email, user_id = await self._authorize(project_id, user)
        billing_owner = str(project.get("created_by") or "").strip().lower()
        try:
            context = await self.gateway.resolve(project_id, request)
        except LLMProviderError as exc:
            raise AIUsageError(exc.code, 400, str(exc)) from None
        except Exception:
            raise AIUsageError("AI_CONFIGURATION_ERROR", 503, "AI is not configured for this project.") from None
        bounded_request = replace(
            request, model=context.model,
            max_tokens=min(request.max_tokens or policy.max_output_tokens, policy.max_output_tokens),
        )
        await self._take_rate_limit(policy, project_id, user_id)
        concurrency_key = await self._take_concurrency(policy, project_id, user_id)

        reservation = None
        usage_id = f"AIU-{uuid4().hex}"
        started_at = self.now()
        try:
            reservation = await self._reserve(billing_owner, policy, started_at)
            record = self._record(usage_id, project_id, user_id, email, billing_owner, policy, context, request, started_at, reservation)
            await self.db["ai_usage_records"].insert_one(record)
            try:
                response = await self.gateway.generate_resolved(context, bounded_request)
            except Exception as exc:
                consume = self._consume_failed_attempt(exc)
                if not consume:
                    await self._release_reservation(billing_owner, policy, reservation)
                await self._finish_failed(usage_id, exc, policy.credit_cost if consume else 0)
                self._log_provider_failure(policy, project_id, context, bounded_request, usage_id, exc)
                if isinstance(exc, LLMProviderError):
                    raise
                raise AIUsageError("AI_PROVIDER_FAILED", 502, "The AI provider could not complete the request.") from None
            await self.db["ai_usage_records"].update_one(
                {"usage_id": usage_id},
                {"$set": {
                    "status": "SUCCEEDED", "credits_consumed": policy.credit_cost,
                    "provider_id": response.provider_id, "model": response.model,
                    "input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens, "completed_at": self.now(),
                }},
            )
            logger.info(
                "AI operation completed operation=%s project=%s provider=%s model=%s status=SUCCEEDED tokens=%s",
                policy.operation.value, project_id, response.provider_id, response.model, response.total_tokens,
            )
            return response
        except Exception:
            if reservation is not None and not await self.db["ai_usage_records"].find_one({"usage_id": usage_id}):
                await self._release_reservation(billing_owner, policy, reservation)
            raise
        finally:
            await self._release_concurrency(concurrency_key)

    async def _authorize(self, project_id: str, user: dict) -> tuple[dict, str, str]:
        email, user_id = _identity(user)
        project = await self.db["projects"].find_one({"project_id": project_id})
        if not project or not email:
            raise AIUsageError("AI_ACCESS_DENIED", 404, "Project not found or access denied.")
        owner = str(project.get("created_by") or "").strip().lower()
        if owner != email:
            membership = await self.db["project_memberships"].find_one({
                "project_id": project_id, "email": email, "status": "ACTIVE",
            })
            if not membership:
                raise AIUsageError("AI_ACCESS_DENIED", 404, "Project not found or access denied.")
        return project, email, user_id

    async def _reserve(self, billing_owner: str, policy: AIUsagePolicy, now: datetime) -> dict:
        start, end = _month_period(now)
        start_value, end_value = start.isoformat(), end.isoformat()
        users = self.db["users"]
        await users.update_one(
            {"email": billing_owner, "subscription.ai_usage_period_start": {"$ne": start_value}},
            {"$set": {
                "subscription.usage.ai_gen_used": 0,
                "subscription.ai_usage_period_start": start_value,
                "subscription.ai_usage_period_end": end_value,
            }},
        )
        owner = await users.find_one({"email": billing_owner})
        if not owner or owner.get("subscription", {}).get("status") != "active":
            raise AIUsageError("AI_USAGE_LIMIT_EXCEEDED", 403, "No active AI allowance is available.")
        allowance = owner.get("subscription", {}).get("limits", {}).get("ai_gen_limit")
        query = {"email": billing_owner, "subscription.ai_usage_period_start": start_value}
        if allowance is not None:
            query["subscription.usage.ai_gen_used"] = {"$lte": max(allowance - policy.credit_cost, -1)}
        updated = await users.find_one_and_update(
            query, {"$inc": {"subscription.usage.ai_gen_used": policy.credit_cost}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            raise AIUsageError("AI_USAGE_LIMIT_EXCEEDED", 403, "The AI usage allowance has been reached.")
        return {"period_start": start_value, "period_end": end_value, "allowance": allowance}

    async def _release_reservation(self, billing_owner: str, policy: AIUsagePolicy, reservation: dict) -> None:
        await self.db["users"].update_one(
            {"email": billing_owner, "subscription.ai_usage_period_start": reservation["period_start"]},
            {"$inc": {"subscription.usage.ai_gen_used": -policy.credit_cost}},
        )

    def _record(self, usage_id: str, project_id: str, user_id: str, email: str, billing_owner: str,
                policy: AIUsagePolicy, context: ResolvedLLMContext, request: LLMRequest,
                started_at: datetime, reservation: dict) -> dict:
        return {
            "usage_id": usage_id, "project_id": project_id, "user_id": user_id, "user_email": email,
            "billing_owner": billing_owner, "operation_type": policy.operation.value, "ai_mode": context.mode,
            "provider_id": context.provider_id, "model": context.model, "credits_reserved": policy.credit_cost,
            "credits_consumed": 0, "input_units": len(request.prompt), "input_unit_type": "CHARACTERS",
            "prompt_key": request.prompt_key, "prompt_version": request.prompt_version,
            "input_tokens": None, "output_tokens": None, "total_tokens": None, "status": "STARTED",
            "started_at": started_at, "completed_at": None, "billing_period_start": reservation["period_start"],
            "billing_period_end": reservation["period_end"], "estimated_managed_cost": None,
            "cost_currency": None, "managed_cost_eligible": context.mode == "MANAGED",
        }

    async def _finish_failed(self, usage_id: str, exc: Exception, credits_consumed: int) -> None:
        code = exc.code if isinstance(exc, LLMProviderError) else "AI_PROVIDER_FAILED"
        await self.db["ai_usage_records"].update_one(
            {"usage_id": usage_id},
            {"$set": {"status": "FAILED", "error_code": code, "credits_consumed": credits_consumed, "completed_at": self.now()}},
        )

    @staticmethod
    def _log_provider_failure(policy: AIUsagePolicy, project_id: str, context: ResolvedLLMContext,
                              request: LLMRequest, usage_id: str, exc: Exception) -> None:
        provider_error = exc if isinstance(exc, LLMProviderError) else None
        logger.warning(
            "AI operation failed operation=%s project=%s provider=%s model=%s status=FAILED "
            "error_code=%s provider_status=%s provider_error_type=%s provider_error_code=%s "
            "provider_error_param=%s structured_output=%s schema_name=%s usage_id=%s",
            policy.operation.value, project_id, context.provider_id, context.model,
            provider_error.code if provider_error else "AI_PROVIDER_FAILED",
            provider_error.status_code if provider_error else None,
            provider_error.provider_error_type if provider_error else None,
            provider_error.provider_error_code if provider_error else None,
            provider_error.provider_error_param if provider_error else None,
            request.response_schema is not None, request.response_schema_name, usage_id,
        )

    @staticmethod
    def _consume_failed_attempt(exc: Exception) -> bool:
        if isinstance(exc, LLMProviderError):
            return exc.code in {"TIMEOUT", "PROVIDER_UNAVAILABLE"}
        return True

    async def _take_rate_limit(self, policy: AIUsagePolicy, project_id: str, user_id: str) -> None:
        key = f"ai:rate:{project_id}:{user_id}:{policy.operation.value}"
        self._require_distributed_limiter()
        try:
            count = await asyncio.to_thread(self.redis.incr, key)
            if count == 1:
                await asyncio.to_thread(self.redis.expire, key, policy.rate_limit_window_seconds)
        except Exception:
            raise AIUsageError("AI_LIMITER_UNAVAILABLE", 503, "AI request controls are temporarily unavailable.") from None
        if count > policy.rate_limit_requests:
            raise AIUsageError("AI_RATE_LIMITED", 429, "Too many AI requests. Try again later.")

    async def _take_concurrency(self, policy: AIUsagePolicy, project_id: str, user_id: str) -> str:
        key = f"ai:concurrency:{project_id}:{user_id}:{policy.operation.value}"
        self._require_distributed_limiter()
        try:
            count = await asyncio.to_thread(self.redis.incr, key)
            if count == 1:
                await asyncio.to_thread(self.redis.expire, key, policy.concurrency_ttl_seconds)
        except Exception:
            raise AIUsageError("AI_LIMITER_UNAVAILABLE", 503, "AI request controls are temporarily unavailable.") from None
        if count > policy.max_concurrent_requests:
            try:
                await asyncio.to_thread(self.redis.decr, key)
            except Exception:
                logger.warning("AI rejected concurrency increment could not be released")
            raise AIUsageError("AI_CONCURRENCY_LIMIT", 429, "Another AI operation is already running.")
        return key

    def _require_distributed_limiter(self) -> None:
        if settings.app_env.lower() == "production" and isinstance(self.redis, redis_module.LocalCache):
            raise AIUsageError("AI_LIMITER_UNAVAILABLE", 503, "AI request controls are temporarily unavailable.")

    async def _release_concurrency(self, key: str) -> None:
        try:
            remaining = await asyncio.to_thread(self.redis.decr, key)
            if remaining <= 0:
                await asyncio.to_thread(self.redis.delete, key)
        except Exception:
            # The bounded TTL releases abandoned slots even if Redis fails here.
            logger.warning("AI concurrency slot release failed")
