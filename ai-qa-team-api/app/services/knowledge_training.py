"""Resumable review coordination. Never approves knowledge or automatically retries AI."""
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.models.product_knowledge import KnowledgeDraft, KnowledgeSourceInput
from app.services.product_knowledge import ProductKnowledge
from app.services.approved_visual_run import digest
from app.utils.feature_flags import require_features


def now():
    return datetime.now(timezone.utc).isoformat()


class KnowledgeTraining:
    def __init__(self, database, knowledge=None):
        self.db = database
        self.knowledge = knowledge or ProductKnowledge(database)
        self.rows = database["knowledge_training_reviews"]

    @staticmethod
    def key(project, identity):
        return digest({"project": project, "review": identity})

    @staticmethod
    def public(row):
        return {key: value for key, value in row.items()
                if key not in ("_id", "source_input", "input_digest")}

    async def row(self, project, identity):
        require_features("product_knowledge")
        row = await self.rows.find_one({"_id": self.key(project, identity), "project_id": project})
        if not row:
            raise HTTPException(404, "Training review not found.")
        return row

    async def get(self, project, identity, *, _listed_row=None):
        row = _listed_row if _listed_row is not None else await self.row(project, identity)
        if row["extraction_state"] == "running" and row["lease_expires_at"] < now():
            await self.rows.update_one({"_id": row["_id"], "extraction_state": "running", "attempt": row["attempt"]},
                {"$set": {"extraction_state": "uncertain", "updated_at": now()}})
            row = await self.row(project, identity)
        # Recover a lost save acknowledgement using the server-owned draft ID.
        if row["state"] in ("saving", "saved"):
            version = await self.db["product_knowledge_versions"].find_one({
                "project_id": project, "_id": row["draft_version_id"]})
            if version:
                row = {**row, "state": "saved", "saved_version": self.knowledge.public(
                    await self.knowledge.approved_view(project, version))}
        result = self.public(row)
        if row["removed_claim_ids"] and result.get("saved_version", {}).get("status") != "approved":
            result["removal_impact"] = await self.removal_impact(project, row["removed_claim_ids"], row["base_version_id"])
        return result

    async def removal_impact(self, project, claim_ids, version_id):
        result = {}
        # Include records pinned to this knowledge version conservatively, even
        # when legacy records lack granular rule references. Never touch executions.
        for collection, identity in (("scenarios", "scenario_id"), ("testcases", "testcase_id")):
            rows = await self.db[collection].find({"project_id": project}).to_list(10000)
            if len(rows) == 10000:
                raise HTTPException(409, "Removal impact exceeds the supported review size. Review project dependencies before removal.")
            result[collection] = [{"id": row.get(identity), "title": row.get("title", "Untitled")}
                for row in rows if set(row.get("rule_references") or []) & set(claim_ids)
                or (version_id and row.get("knowledge_version_id") == version_id)]
        return result

    async def listing(self, project):
        require_features("product_knowledge")
        rows = await self.rows.find({"project_id": project}).sort("created_at", -1).to_list(50)
        slots=asyncio.Semaphore(8)
        async def present(row):
            async with slots:return await self.get(project,row["review_id"],_listed_row=row)
        return await asyncio.gather(*(present(row) for row in rows))

    async def start(self, project, actor, payload):
        require_features("product_knowledge")
        if payload.source_id:
            await self.knowledge.record("product_knowledge_sources", project, payload.source_id)
            previous_review = await self.rows.find_one({"project_id": project, "source_id": payload.source_id})
            if previous_review:
                return await self.get(project, previous_review["review_id"])
        identity = payload.source_id or payload.request_id
        key = self.key(project, identity)
        existing = await self.rows.find_one({"_id": key, "project_id": project})
        fingerprint = digest(payload.model_dump(exclude={"request_id"}))
        if existing:
            if existing["input_digest"] != fingerprint:
                raise HTTPException(409, "This training request already has different inputs.")
            return await self.get(project, identity)
        base = await self.knowledge.active(project)
        proposals = []; removals = []
        if payload.mode != "training":
            claim = next((item for item in (base or {}).get("claims", []) if item["claim_id"] == payload.claim_id), None)
            if not claim:
                raise HTTPException(409, "Choose a rule from current approved knowledge.")
            if payload.mode == "correction":
                proposals = [{"claim": claim, "decision": "pending"}]
            else:
                removals = [payload.claim_id]
        if payload.source_id:
            await self.knowledge.record("product_knowledge_sources", project, payload.source_id)
        source_input = payload.source.model_dump() if payload.source else None
        source_origin = {}
        if payload.story_id:
            story = await self.knowledge.story(project, payload.story_id)
            source_input = KnowledgeSourceInput(title=("Story: " + str(story["title"]))[:240], kind="document",
                text="\n".join(str(story.get(key) or "") for key in
                    ("title", "description", "acceptance_criteria", "out_of_scope"))).model_dump()
            source_origin = {"kind": "story", "story_id": payload.story_id, "story_digest": digest(story)}
        row = {"_id": key, "project_id": project, "review_id": identity, "title": payload.title,
            "mode": payload.mode, "input_digest": fingerprint, "source_input": source_input, "source_origin": source_origin,
            "source_id": payload.source_id, "base_version_id": base["version_id"] if base else None,
            "state": "reviewing", "extraction_state": "not_started" if payload.mode == "training" else "completed",
            "attempt": 0, "revision": 0, "proposals": proposals, "clarification_questions": [],
            "clarification_answers": {}, "removed_claim_ids": removals, "draft_version_id": uuid4().hex,
            "created_by": actor, "created_at": now(), "updated_at": now()}
        try:
            await self.rows.insert_one(row)
        except DuplicateKeyError:
            existing = await self.rows.find_one({"_id": key, "project_id": project})
            if not existing or existing["input_digest"] != fingerprint:
                raise HTTPException(409, "This training request already exists. Refresh status.") from None
            return await self.get(project, identity)
        return self.public(row)

    async def extract(self, project, user, identity, payload):
        row = await self.row(project, identity)
        if row["extraction_state"] == "completed":
            return await self.get(project, identity)
        if row["state"] != "reviewing" or row["extraction_state"] == "running":
            raise HTTPException(409, "Extraction is in progress. Refresh status; do not resubmit.")
        if row["extraction_state"] == "uncertain" and not (payload.retry_uncertain and payload.expected_attempt == row["attempt"]):
            raise HTTPException(409, "Extraction outcome is uncertain. An explicit retry may spend another AI request.")
        attempt = row["attempt"] + 1
        locked = await self.rows.find_one_and_update({"_id": row["_id"], "revision": row["revision"],
            "extraction_state": row["extraction_state"], "state": "reviewing"}, {"$set": {
                "extraction_state": "running", "attempt": attempt, "revision": row["revision"] + 1,
                "lease_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=180)).isoformat(), "updated_at": now()}},
            return_document=ReturnDocument.AFTER)
        if not locked:
            raise HTTPException(409, "Training changed. Reload before continuing.")
        try:
            source_id = row["source_id"]
            if not source_id:
                # An interrupted source insert is recovered by its server-owned origin.
                source = await self.db["product_knowledge_sources"].find_one({"project_id": project,
                    "origin.training_review_id": identity})
                if not source:
                    source = await self.knowledge.add_source(project, row["created_by"],
                        KnowledgeSourceInput.model_validate(row["source_input"]),
                        origin={**row.get("source_origin", {}), "training_review_id": identity})
                source_id = source["source_id"]
                await self.rows.update_one({"_id": row["_id"], "attempt": attempt},
                    {"$set": {"source_id": source_id, "source_input": None}})
            result = await asyncio.wait_for(self.knowledge.extract(project, user, source_id, no_automatic_retry=True), timeout=150)
            await self.rows.update_one({"_id": row["_id"], "attempt": attempt, "extraction_state": "running"},
                {"$set": {"extraction_state": "completed", "proposals": [
                    {"claim": claim.model_dump(), "decision": "pending"} for claim in result.claims],
                    "clarification_questions": result.clarification_questions,
                    "clarification_answers": {question: "" for question in result.clarification_questions}, "updated_at": now()}})
        except BaseException:
            # Never change completed results after a lost database acknowledgement.
            await asyncio.shield(self.rows.update_one({"_id": row["_id"], "attempt": attempt, "extraction_state": "running"},
                {"$set": {"extraction_state": "uncertain", "updated_at": now()}}))
            raise
        return await self.get(project, identity)

    async def review(self, project, identity, payload):
        row = await self.row(project, identity)
        if row["state"] != "reviewing" or row["extraction_state"] != "completed":
            raise HTTPException(409, "This review is not editable. Refresh its status.")
        original_ids = {item["claim"]["claim_id"] for item in row["proposals"]}
        submitted_ids = [item.claim.claim_id for item in payload.proposals]
        if set(submitted_ids) != original_ids or len(submitted_ids) != len(original_ids):
            raise HTTPException(422, "Keep proposal identities intact; reject rather than delete proposals.")
        if set(payload.clarification_answers) != set(row["clarification_questions"]):
            raise HTTPException(422, "Keep clarification questions intact.")
        if any(len(answer) > 2000 for answer in payload.clarification_answers.values()):
            raise HTTPException(422, "Keep clarification answers within 2000 characters.")
        await self.knowledge.validate_claims(project, [item.claim for item in payload.proposals])
        if len(payload.model_dump_json()) > 120000:
            raise HTTPException(413, "Review exceeds supported bounds.")
        updated = await self.rows.find_one_and_update({"_id": row["_id"], "revision": payload.expected_revision,
            "state": "reviewing", "extraction_state": "completed"}, {"$set": {
                "proposals": [item.model_dump() for item in payload.proposals],
                "clarification_answers": payload.clarification_answers, "revision": payload.expected_revision + 1,
                "removal_reason": payload.removal_reason,
                "updated_at": now()}}, return_document=ReturnDocument.AFTER)
        if not updated:
            raise HTTPException(409, "Another reviewer saved changes. Reload before editing further.")
        return await self.get(project, identity)

    async def rebase(self, project, actor, identity, payload):
        row = await self.row(project, identity)
        if row["state"] == "rejected":
            raise HTTPException(409, "Discarded reviews cannot be resumed. Start intentional new training.")
        if row["revision"] != payload.expected_revision or row["extraction_state"] != "completed":
            raise HTTPException(409, "Reload the completed review before continuing.")
        if (await self.get(project, identity)).get("saved_version", {}).get("status") == "approved":
            raise HTTPException(409, "Approved training is immutable. Start additional training or an explicit correction.")
        current = await self.knowledge.active(project)
        base = current["version_id"] if current else None
        if base == row["base_version_id"]:
            return await self.get(project, identity)
        targets = row["removed_claim_ids"] or ([item["claim"]["claim_id"] for item in row["proposals"]] if row["mode"] == "correction" else [])
        if set(targets) - {claim["claim_id"] for claim in (current or {}).get("claims", [])}:
            raise HTTPException(409, "The targeted rule was removed. Inspect current knowledge before proposing another correction.")
        fingerprint = digest({"from_review": identity, "revision": row["revision"], "base": base})
        copy = {**row, "_id": self.key(project, payload.request_id), "review_id": payload.request_id,
            "input_digest": fingerprint, "base_version_id": base, "revision": 0, "state": "reviewing",
            "draft_version_id": uuid4().hex, "created_by": actor, "created_at": now(), "updated_at": now(),
            "proposals": [{**item, "decision": "pending" if item["decision"] != "rejected" else "rejected"} for item in row["proposals"]]}
        try:
            await self.rows.insert_one(copy)
        except DuplicateKeyError:
            existing = await self.row(project, payload.request_id)
            if existing["input_digest"] != fingerprint:
                raise HTTPException(409, "This review request has different inputs.") from None
        return await self.get(project, payload.request_id)

    async def discard(self, project, actor, identity, payload):
        row = await self.row(project, identity)
        if row["state"] == "rejected":
            return self.public(row)
        # Only editable reviews can be discarded. Saved immutable drafts may be
        # concurrently approved; do not pretend to revoke an approval here.
        if row["state"] != "reviewing" or row["extraction_state"] == "running":
            raise HTTPException(409, "Only an editable, non-running review can be discarded.")
        closed = await self.rows.find_one_and_update({"_id": row["_id"], "project_id": project,
            "revision": payload.expected_revision, "state": "reviewing", "extraction_state": row["extraction_state"]},
            {"$set": {"state": "rejected", "revision": row["revision"] + 1, "proposals": [],
                "removed_claim_ids": [], "clarification_questions": [], "clarification_answers": {},
                "source_input": None, "removal_reason": "", "completed_by": actor,
                "completed_at": now(), "updated_at": now()}}, return_document=ReturnDocument.AFTER)
        if not closed:
            raise HTTPException(409, "Review changed. Refresh status before discarding.")
        return self.public(closed)

    async def save(self, project, actor, identity, payload):
        row = await self.row(project, identity)
        recovered = await self.get(project, identity)
        if recovered["state"] in ("saved", "rejected"):
            return recovered
        if row["state"] == "saving" and row.get("save_lease_expires_at", "") > now():
            raise HTTPException(409, "Saving is in progress. Refresh status before retrying.")
        if row["extraction_state"] != "completed" or row["revision"] != payload.expected_revision:
            raise HTTPException(409, "Reload the completed review before saving.")
        if row["removed_claim_ids"] and not row.get("removal_reason", "").strip():
            raise HTTPException(409, "Explain why this knowledge is being removed before review.")
        if (row["state"] == "reviewing" and not row["removed_claim_ids"]
                and all(item["decision"] == "rejected" for item in row["proposals"])):
            # Discarding is not knowledge approval. Clear rejected review content;
            # retain request identity to prevent replaying a metered extraction.
            closed = await self.rows.find_one_and_update({"_id": row["_id"],
                "revision": payload.expected_revision, "state": "reviewing"}, {"$set": {
                    "state": "rejected", "revision": payload.expected_revision + 1,
                    "proposals": [], "clarification_questions": [], "clarification_answers": {},
                    "source_input": None,
                    "completed_by": actor, "completed_at": now(), "updated_at": now()}},
                return_document=ReturnDocument.AFTER)
            if not closed:
                raise HTTPException(409, "Review changed. Refresh status.")
            return await self.get(project, identity)
        if any(item["decision"] not in ("confirmed", "rejected") for item in row["proposals"]) or any(
                not answer.strip() for answer in row["clarification_answers"].values()):
            raise HTTPException(409, "Confirm or reject proposals and answer every clarification before saving.")
        if any(item["decision"] == "confirmed" and item.get("clarification_question", "").strip()
               and not item.get("clarification_answer", "").strip() for item in row["proposals"]):
            raise HTTPException(409, "Answer the proposal clarification before confirming this change.")
        if not any(item["decision"] == "confirmed" for item in row["proposals"]) and not row["removed_claim_ids"]:
            raise HTTPException(409, "No accepted knowledge change to save. Rejected proposals leave approved knowledge untouched.")
        base = await self.knowledge.active(project)
        if (base["version_id"] if base else None) != row["base_version_id"]:
            raise HTTPException(409, "Approved knowledge changed. Keep this review and start a new review against current knowledge.")
        locked = await self.rows.find_one_and_update({"_id": row["_id"], "revision": row["revision"], "state": row["state"]},
            {"$set": {"state": "saving", "save_lease_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=180)).isoformat(),
                      "updated_at": now()}}, return_document=ReturnDocument.AFTER)
        if not locked:
            raise HTTPException(409, "Review changed. Refresh status.")
        try:
            version = await self.knowledge.create_version(project, actor, KnowledgeDraft(title=row["title"],
                parent_version_id=row["base_version_id"], claims=[item["claim"] for item in row["proposals"] if item["decision"] == "confirmed"],
                removed_claim_ids=row["removed_claim_ids"], clarification_answers={**row["clarification_answers"], **{
                    item["clarification_question"]: item["clarification_answer"] for item in row["proposals"]
                    if item["decision"] == "confirmed" and item.get("clarification_question", "").strip()}},
                removal_reasons={key: row["removal_reason"] for key in row["removed_claim_ids"]}),
                version_id=row["draft_version_id"])
            if version["parent_version_id"] != row["base_version_id"]:
                raise HTTPException(409, "Knowledge changed during save. Review current knowledge; no approval was performed.")
            await self.rows.update_one({"_id": row["_id"], "state": "saving"}, {"$set": {"state": "saved", "updated_at": now()}})
        except BaseException:
            await asyncio.shield(self.rows.update_one({"_id": row["_id"], "state": "saving"},
                {"$set": {"state": "reviewing", "updated_at": now()}}))
            raise
        return await self.get(project, identity)
