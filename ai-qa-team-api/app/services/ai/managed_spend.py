"""Conservative USD reservations, independent of customer request allowances.

Only qualified pinned OpenAI text models are supported. Reserve the full published
context window plus bounded output; never estimate a dollar ceiling from characters.
No automatic release of submitted/unknown work, and no provider call in a transaction.
"""
from copy import deepcopy
from datetime import datetime, timezone

from fastapi import HTTPException
from app.config import settings
from app.services.ai.ai_usage_policy import AIUsageError
from app.services.resource_quota import ResourceQuota, fingerprint

MODELS = {"gpt-4o-mini-2024-07-18": (128000, 16384)}
ALIASES = {"gpt-4o-mini": "gpt-4o-mini-2024-07-18"}


async def guard_active(database):
    if settings.features.managed_spend_guard:
        return True
    control = await database["ai_spend_control"].find_one({"_id": "managed"})
    return bool((control or {}).get("initialized"))


async def claim_call(database, context, request):
    if context.mode != "MANAGED" or not await guard_active(database):
        return
    if not request.spend_reservation_id or request.max_retries != 0 or not request.max_tokens or request.max_tokens < 1:
        raise AIUsageError("MANAGED_SPEND_ADMISSION_REQUIRED", 503, "A metered Managed AI admission is required.")
    control = await database["ai_spend_control"].find_one({"_id": "managed"})
    if not control or not control.get("initialized") or control.get("halted"):
        raise AIUsageError("MANAGED_SPEND_REVIEW_REQUIRED", 503, "Managed AI cost review is required.")
    result = await database["ai_spend_reservations"].update_one({"_id": request.spend_reservation_id,
        "state": "SUBMITTED", "model": context.model, "output_bound": {"$gte": request.max_tokens or 0}},
        {"$set": {"state": "CALLING", "call_started_at": datetime.now(timezone.utc)}})
    if result.matched_count != 1:
        raise AIUsageError("MANAGED_SPEND_ADMISSION_REQUIRED", 503, "A metered Managed AI admission is required.")


def cost(input_tokens, output_tokens, rates):
    return (input_tokens * rates["input_micro_usd_per_million"] + output_tokens * rates["output_micro_usd_per_million"] + 999999) // 1000000


def qualified_model(model, max_output_tokens):
    if not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool) or max_output_tokens < 1:
        raise AIUsageError("MANAGED_OUTPUT_BOUND_REQUIRED", 422, "A positive AI output bound is required.")
    resolved = ALIASES.get(model, model)
    config = settings.managed_spend
    rates = config.models.get(resolved)
    if (resolved not in MODELS or not rates or not config.pricing_revision or not config.rates_verified
            or config.per_request_micro_usd <= 0 or config.platform_monthly_micro_usd <= 0):
        raise AIUsageError("MANAGED_SPEND_NOT_CONFIGURED", 503, "Managed AI cost controls require configuration.")
    context, maximum_output = MODELS[resolved]
    output = min(max_output_tokens, maximum_output)
    amount = cost(context, output, rates.model_dump())
    if amount > config.per_request_micro_usd:
        raise AIUsageError("MANAGED_REQUEST_BUDGET", 403, "This AI request exceeds the configured cost ceiling.")
    return resolved, {"rates": rates.model_dump(), "input_bound": context, "output_bound": output,
        "reserved_micro_usd": amount, "pricing_revision": config.pricing_revision}


class ManagedSpend:
    def __init__(self, database):
        self.db = database
        self.quota = ResourceQuota(database)

    async def reserve(self, usage_id, owner, plan, model, max_output_tokens, *, now=None):
        model, pricing = qualified_model(model, max_output_tokens)
        now = now or datetime.now(timezone.utc)
        period = now.strftime("%Y-%m")
        account_limit = settings.managed_spend.account_monthly_micro_usd.get(plan, 0)
        if not isinstance(account_limit, int) or isinstance(account_limit, bool) or account_limit <= 0:
            raise AIUsageError("MANAGED_SPEND_NOT_CONFIGURED", 503, "Managed AI account budget requires configuration.")
        keys = [fingerprint(["account", owner, period]), fingerprint(["platform", period])]
        for key in keys:
            await self.db["ai_spend_budgets"].update_one({"_id": key}, {"$setOnInsert": {
                "spent_micro_usd": 0, "reserved_micro_usd": 0, "period": period}}, upsert=True)
        record = {"_id": usage_id, "owner": owner, "period": period, "model": model, "currency": "USD",
            "state": "RESERVED", "budget_ids": keys, "created_at": now, **pricing}

        async def work(session):
            control = await self.db["ai_spend_control"].find_one({"_id": "managed"}, session=session)
            if not control or not control.get("initialized") or not settings.managed_spend.cutover_id or control.get("cutover_id") != settings.managed_spend.cutover_id:
                raise AIUsageError("MANAGED_SPEND_NOT_CONFIGURED", 503, "Managed spend cutover requires review.")
            if control.get("halted"):
                raise AIUsageError("MANAGED_SPEND_REVIEW_REQUIRED", 503, "Managed AI cost review is required.")
            for key, limit in zip(keys, (account_limit, settings.managed_spend.platform_monthly_micro_usd)):
                budget = await self.db["ai_spend_budgets"].find_one({"_id": key}, session=session)
                values = [budget.get("spent_micro_usd"), budget.get("reserved_micro_usd")]
                if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
                    raise AIUsageError("MANAGED_SPEND_REVIEW_REQUIRED", 503, "Managed AI cost review is required.")
                if sum(values) + pricing["reserved_micro_usd"] > limit:
                    raise AIUsageError("MANAGED_SPEND_LIMIT", 403, "Managed AI budget reached. Manual work stays available.")
                await self.db["ai_spend_budgets"].update_one({"_id": key}, {"$inc": {"reserved_micro_usd": pricing["reserved_micro_usd"]}}, session=session)
            await self.db["ai_spend_reservations"].insert_one(record, session=session)
            return record
        return await self.quota.transaction(work)

    async def submitted(self, record):
        result = await self.db["ai_spend_reservations"].update_one({"_id": record["_id"], "state": "RESERVED"},
            {"$set": {"state": "SUBMITTED", "submitted_at": datetime.now(timezone.utc)}})
        if result.matched_count != 1:
            raise AIUsageError("MANAGED_SPEND_REVIEW_REQUIRED", 503, "AI cost admission could not be confirmed.")

    async def unknown(self, record):
        await self.db["ai_spend_reservations"].update_one({"_id": record["_id"], "state": {"$in": ["SUBMITTED", "CALLING", "UNKNOWN"]}},
            {"$set": {"state": "UNKNOWN"}})

    async def settle(self, record, *, input_tokens=None, output_tokens=None, response_model=None, release_unsubmitted=False, rejected=False, proof=None):
        if rejected or release_unsubmitted:
            amount = 0
        elif any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (input_tokens, output_tokens)):
            await self.unknown(record); return
        else:
            amount = cost(input_tokens, output_tokens, record["rates"])
            if (input_tokens > record["input_bound"] or output_tokens > record["output_bound"]
                    or response_model != record["model"] or amount > record["reserved_micro_usd"]):
                await self.unknown(record)
                await self.db["ai_spend_control"].update_one({"_id": "managed"}, {"$set": {"halted": True, "usage_id": record["_id"]}}, upsert=True)
                raise AIUsageError("MANAGED_SPEND_REVIEW_REQUIRED", 503, "Managed AI cost review is required.")

        async def work(session):
            row = await self.db["ai_spend_reservations"].find_one({"_id": record["_id"]}, session=session)
            if not row or row["state"] in ("SETTLED", "RELEASED"):
                return
            if proof and proof.get("record_digest") != fingerprint(row):
                raise HTTPException(409, "Spend evidence changed. Review a new reconciliation plan.")
            if release_unsubmitted and row["state"] != "RESERVED":
                return  # Submitted/unknown work is never expired/refunded automatically.
            if not release_unsubmitted and row["state"] == "RESERVED" and not proof:
                raise HTTPException(409, "AI request was not admitted for submission.")
            for key in row["budget_ids"]:
                result = await self.db["ai_spend_budgets"].update_one({"_id": key, "reserved_micro_usd": {"$gte": row["reserved_micro_usd"]}},
                    {"$inc": {"reserved_micro_usd": -row["reserved_micro_usd"], "spent_micro_usd": amount}}, session=session)
                if result.matched_count != 1:
                    raise HTTPException(409, "Managed spend reconciliation is required.")
            await self.db["ai_spend_reservations"].update_one({"_id": row["_id"]}, {"$set": {
                "state": "RELEASED" if rejected or release_unsubmitted else "SETTLED", "actual_micro_usd": amount,
                "input_tokens": input_tokens, "output_tokens": output_tokens, "completed_at": datetime.now(timezone.utc)}}, session=session)
            if proof:
                await self.db["ai_spend_reconciliations"].insert_one({"_id": row["_id"], "proof": deepcopy(proof),
                    "actual_micro_usd": amount, "at": datetime.now(timezone.utc)}, session=session)
        await self.quota.transaction(work)
