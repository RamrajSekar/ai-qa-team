"""Project-authorized, append-only attempt bug links; never fetch or publish URLs."""
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from pydantic import ValidationError

from app.models.attempt_bug import BugDraft, BugAISuggestion
from app.services.approved_visual_run import digest
from app.services.ai.ai_usage_policy import AIOperation
from app.services.ai.ai_usage_service import AIUsageService
from app.services.ai.base_provider import LLMRequest
from app.services.prompt_registry_service import get_active


class AttemptBugs:
    def __init__(self, database): self.db = database

    async def attempt(self, project, run):
        row = await self.db["test_results"].find_one({"project_id": project, "run_id": run})
        if not row: raise HTTPException(404, "Attempt not found in this project.")
        if row["verdict"] != "failed": raise HTTPException(409, "Bug actions require a failed attempt.")
        return row

    @staticmethod
    def public(row): return {k: v for k, v in row.items() if k not in {"_id", "request_digest"}}

    async def preview(self, project, run):
        row = await self.attempt(project, run)
        case = row["specification"]["case"]
        context = [f"Test: {case['title']}", f"Mode: {row['mode']}", f"Recorded: {row['recorded_at']}"]
        if case.get("role"): context.append(f"Application role: {case['role']}")
        if case.get("preconditions"): context.append("Preconditions: " + "; ".join(case["preconditions"]))
        missing = ["Reproduction frequency and severity have not been supplied."]
        if row.get("environment"):
            context.append(f"Environment: {row['environment'].get('name') or row['environment']['env_id']}")
        else: missing.append("Environment was not specified.")
        if row.get("execution_id"):
            execution = await self.db["manual_test_executions"].find_one({"project_id": project, "execution_id": row["execution_id"]})
            if execution: context.append(f"Release / Cycle: {execution['manifest']['release_cycle']}")
        return BugDraft(title=f"Failure: {case['title']}"[:240], summary="Human-reported failure; review reproduction details before sharing.",
            steps=[s["instruction"] for s in case["procedure"]],
            expected_result="\n".join([s["expected"] for s in case["procedure"]] + case.get("assertions", []))[:8000],
            actual_result=row["actual_result"], context="\n".join(context)[:4000], missing_information=missing).model_dump()

    async def links(self, project, run):
        await self.attempt(project, run)
        rows = await self.db["test_attempt_bugs"].find({"project_id": project, "run_id": run}).sort("created_at", -1).limit(50).to_list(50)
        return [self.public(row) for row in rows]

    async def save(self, project, run, actor, payload):
        row = await self.attempt(project, run)
        fingerprint = digest(payload.model_dump())
        key = digest({"project": project, "run": run, "key": payload.idempotency_key})
        existing = await self.db["test_attempt_bugs"].find_one({"_id": key, "project_id": project, "run_id": run})
        if existing:
            if existing["request_digest"] != fingerprint: raise HTTPException(409, "Bug save key was reused with different content.")
            return self.public(existing)
        proposal = None
        if payload.proposal_id:
            proposal = await self.db["test_bug_proposals"].find_one({"proposal_id": payload.proposal_id, "project_id": project, "run_id": run})
            if not proposal: raise HTTPException(404, "AI proposal not found for this attempt.")
        document = {"_id": key, "bug_id": uuid4().hex, "project_id": project, "run_id": run,
            "execution_id": row.get("execution_id"), "testcase_id": row["testcase_id"], "version_id": row["specification"]["version_id"],
            "kind": payload.kind, "status": "draft" if payload.kind == "draft" else "linked", "url": payload.url,
            "draft": payload.draft.model_dump() if payload.draft else None, "source_facts": await self.preview(project, run),
            "proposal_id": payload.proposal_id, "prompt": proposal.get("prompt") if proposal else None,
            "reviewed_by": actor, "created_at": datetime.now(timezone.utc).isoformat(), "request_digest": fingerprint}
        try: await self.db["test_attempt_bugs"].insert_one(document)
        except DuplicateKeyError:
            existing = await self.db["test_attempt_bugs"].find_one({"_id": key, "project_id": project, "run_id": run})
            if not existing or existing["request_digest"] != fingerprint: raise HTTPException(409, "Bug save conflicted.") from None
            return self.public(existing)
        return self.public(document)

    async def draft_ai(self, project, run, user, usage=None):
        facts = await self.preview(project, run)
        # No environment credentials, browser evidence or entire user documents are loaded.
        text = json.dumps(facts)
        text = re.sub(r'(?i)(password|api[_-]?key|token|secret)\s*[:=]\s*[^\s,;"\\]+', r'\1=[REDACTED]', text)
        text = re.sub(r'(?i)Bearer\s+[A-Za-z0-9._-]+|sk-[A-Za-z0-9_-]{16,}', '[REDACTED]', text)
        prompt = await get_active("BUG_REPORT_DRAFT_V1")
        response = await (usage or AIUsageService()).execute(AIOperation.BUG_REPORT_DRAFT, project, user,
            LLMRequest(prompt=text, system_prompt=prompt["system_prompt"], temperature=0,
                response_schema=BugAISuggestion.model_json_schema(), response_schema_name="bug_report_draft_v1",
                prompt_key=prompt["prompt_key"], prompt_version=prompt["resolved_version"]))
        try: suggestion = BugAISuggestion.model_validate(json.loads(response.text))
        except (ValidationError, ValueError, TypeError): raise HTTPException(422, "AI returned an invalid bug draft; use manual drafting.") from None
        # Expected/actual/steps remain supplied facts, regardless of model output.
        draft = {**facts, "summary": suggestion.summary, "missing_information": list(dict.fromkeys(facts["missing_information"] + suggestion.missing_information))[:20]}
        BugDraft.model_validate(draft)
        identity = uuid4().hex
        metadata = {"prompt_key": prompt["prompt_key"], "version": prompt["resolved_version"]}
        await self.db["test_bug_proposals"].insert_one({"_id": identity, "proposal_id": identity, "project_id": project, "run_id": run,
            "draft": draft, "prompt": metadata, "created_by": str(user.get("_id") or user["email"]), "created_at": datetime.now(timezone.utc).isoformat()})
        return {"proposal_id": identity, "draft": draft, "prompt": metadata, "requires_review": True}
