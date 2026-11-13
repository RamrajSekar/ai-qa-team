"""Immutable NLP snapshots with atomic per-case approval and manual-use export."""
from datetime import datetime, timezone
import json
from uuid import uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.services.approved_visual_run import digest
from app.services.knowledge_test_design import KnowledgeTestDesign
from app.services.product_knowledge import ProductKnowledge
from app.utils.feature_flags import require_features
from app.config import settings

MAX_VERSIONS = 50
MAX_VERSION_BYTES = 120000  # <=6MB content per case document, below Mongo's 16MB document limit.


class TestDesignReview:
    def __init__(self, database):
        self.db = database
        self.knowledge = ProductKnowledge(database)

    @staticmethod
    def gate():
        require_features("test_generation")
        if not settings.features.manual_test_results:
            require_features("product_knowledge", "story_analysis")

    @staticmethod
    def scope(project, testcase):
        return {"_id": "design:" + digest([project, testcase]), "project_id": project, "testcase_id": testcase}

    async def document(self, project, testcase):
        self.gate()
        return await self.db["test_design_documents"].find_one(self.scope(project, testcase))

    async def context(self, project, testcase):
        case = await self.db["testcases"].find_one({"project_id": project, "testcase_id": testcase})
        if not case:
            raise HTTPException(404, "Test case not found in this project.")
        scenario = await self.db["scenarios"].find_one({"project_id": project, "scenario_id": case.get("scenario_id")})
        if not scenario or scenario.get("approved") is not True or not scenario.get("story_id"):
            raise HTTPException(409, "Review and approve the source scenario before test design approval.")
        story = await self.knowledge.story(project, scenario["story_id"])
        if not (settings.features.product_knowledge and settings.features.story_analysis):
            if (settings.features.product_knowledge or settings.features.story_analysis
                    or any(record.get("knowledge_version_id") or record.get("story_analysis_id") for record in (case, scenario))):
                raise HTTPException(409, "Knowledge-linked cases require both knowledge and story-analysis review. Manual mode cannot bypass that review.")
            snapshot = {"design_basis": "reviewer-authored-expectations-v1", "story_id": story["story_id"], "scenario_id": scenario["scenario_id"],
                "story_snapshot": story, "story_digest": digest(story),
                "scenario_snapshot": {key: scenario.get(key) for key in ("title", "description", "purpose", "role", "coverage_type", "preconditions", "expected_outcome")},
                "source_digest": digest([case, scenario, story]), "knowledge_version_id": None, "knowledge_digest": None,
                "story_analysis_id": None, "analysis_digest": None, "source_context_changed": False}
            return snapshot, story, {"claims": []}
        reviewed = await self.knowledge.generation_context(project, story["story_id"])
        knowledge, analysis = reviewed["knowledge"], reviewed["analysis"]
        changed = any((record.get("knowledge_version_id") and record["knowledge_version_id"] != knowledge["version_id"])
                      or (record.get("story_analysis_id") and record["story_analysis_id"] != analysis["analysis_id"])
                      for record in (case, scenario))
        snapshot = {"story_id": story["story_id"], "scenario_id": scenario["scenario_id"],
            "story_snapshot": story, "story_digest": digest(story),
            "scenario_snapshot": {key: scenario.get(key) for key in ("title", "description", "purpose", "role", "coverage_type", "preconditions", "expected_outcome")},
            "source_digest": digest([case, scenario, story]),
            "knowledge_version_id": knowledge["version_id"], "knowledge_digest": knowledge["content_digest"],
            "story_analysis_id": analysis["analysis_id"], "analysis_digest": digest(analysis), "source_context_changed": bool(changed)}
        return snapshot, story, knowledge

    async def state(self, project, testcase):
        self.gate()
        # Check existence even when the case has never had a review document.
        if not await self.db["testcases"].find_one({"project_id": project, "testcase_id": testcase}):
            raise HTTPException(404, "Test case not found in this project.")
        document = await self.document(project, testcase)
        versions = list(reversed((document or {}).get("versions", [])))
        current, context_error, rules = None, None, []
        try:
            current, _, knowledge = await self.context(project, testcase)
            rules = [{"claim_id": claim["claim_id"], "statement": claim["statement"]} for claim in knowledge["claims"] if claim["epistemic_status"] == "expected"]
        except HTTPException as exc:
            if exc.status_code not in (404, 409): raise
            context_error = str(exc.detail)
        active_id = (document or {}).get("active_version_id")
        active = next((item for item in versions if item["version_id"] == active_id), None)
        stale = bool(active and (not current or active["context_digest"] != digest(current)))
        return {"active_version_id": active_id, "review_required": not active or stale,
                "context_ready": current is not None, "context_error": context_error,
                "current_context": current, "approved_expected_rules": rules,
                "versions": [{**item, "stale": not current or item["context_digest"] != digest(current)} for item in versions]}

    async def create(self, project, testcase, actor, payload):
        self.gate()
        collection = self.db["test_design_documents"]
        scope = self.scope(project, testcase)
        document = await collection.find_one(scope)
        request_digest = digest(payload.model_dump())
        for item in (document or {}).get("versions", []):
            if item["idempotency_key"] == payload.idempotency_key:
                if item["request_digest"] != request_digest:
                    raise HTTPException(409, "This save key was used with different content.")
                return item
        context, story, knowledge = await self.context(project, testcase)
        if context["source_context_changed"] and not payload.acknowledge_source_changes:
            raise HTTPException(409, "Generated source context changed. Explicitly review the copied content against current approved knowledge before saving a successor.")
        try:
            KnowledgeTestDesign.references(payload.case, story, knowledge)
        except HTTPException as exc:
            raise HTTPException(422, exc.detail) from None
        if len((document or {}).get("versions", [])) >= MAX_VERSIONS:
            raise HTTPException(409, "This case reached its review-history limit. Preserve its history and use an explicitly scoped archival process.")
        parent = payload.parent_version_id or (document or {}).get("active_version_id")
        if parent and not any(item["version_id"] == parent and item["status"] == "approved" for item in (document or {}).get("versions", [])):
            raise HTTPException(422, "A successor must reference an approved version of this case.")
        content = payload.case.model_dump()
        content["public_data"] = {entry.name: entry.value for entry in payload.case.public_data}
        version = {"version_id": uuid4().hex, "schema_version": "nlp-test-design-v1", "status": "draft",
            "parent_version_id": parent, "case": content, "context": context, "context_digest": digest(context),
            "content_digest": digest([content, context]), "created_by": actor, "created_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": payload.idempotency_key, "request_digest": request_digest}
        version["source_changes_acknowledged"] = payload.acknowledge_source_changes
        if len(json.dumps(version, ensure_ascii=False).encode()) > MAX_VERSION_BYTES:
            raise HTTPException(413, "Keep this reviewed case and its source snapshot within 120000 UTF-8 bytes.")
        if document is None:
            try:
                await collection.insert_one({**scope, "revision": 0, "active_version_id": None, "versions": []})
            except DuplicateKeyError:
                pass
            document = await collection.find_one(scope)
            for item in document["versions"]:
                if item["idempotency_key"] == payload.idempotency_key:
                    if item["request_digest"] != request_digest:
                        raise HTTPException(409, "This save key was used with different content.")
                    return item
        updated = await collection.find_one_and_update({**scope, "revision": document["revision"]},
            {"$set": {"versions": [*document["versions"], version], "revision": document["revision"] + 1}},
            return_document=ReturnDocument.AFTER)
        if not updated:
            # Idempotent concurrent save can return the winning exact snapshot.
            latest = await collection.find_one(scope)
            existing = next((item for item in latest["versions"] if item["idempotency_key"] == payload.idempotency_key), None)
            if existing and existing["request_digest"] == request_digest: return existing
            raise HTTPException(409, "Review history changed. Reload before saving again.")
        return version

    async def approve(self, project, testcase, actor, version_id, *, actor_name=None, project_role=None):
        self.gate()
        document = await self.document(project, testcase)
        version = next((item for item in (document or {}).get("versions", []) if item["version_id"] == version_id), None)
        if not version: raise HTTPException(404, "Design version not found in this project/case.")
        if version["status"] == "approved": return version  # Never reactivate an old approval.
        current, _, _ = await self.context(project, testcase)
        if version["context_digest"] != digest(current):
            raise HTTPException(409, "Story, scenario, case or approved knowledge changed. Review a successor draft.")
        if version.get("parent_version_id") != document.get("active_version_id"):
            raise HTTPException(409, "Another version was approved. Review a successor of the current approval.")
        approved = {**version, "status": "approved", "approved_by": actor, "approved_at": datetime.now(timezone.utc).isoformat(),
                    "approved_by_display_name": (actor_name or actor)[:240], "approved_by_project_role": project_role,
                    "approval_policy": "admin_required" if settings.features.test_design_admin_review else "project_member_allowed"}
        versions = [approved if item["version_id"] == version_id else item for item in document["versions"]]
        updated = await self.db["test_design_documents"].find_one_and_update(
            {**self.scope(project, testcase), "revision": document["revision"]},
            {"$set": {"versions": versions, "active_version_id": version_id, "revision": document["revision"] + 1}},
            return_document=ReturnDocument.AFTER)
        if not updated: raise HTTPException(409, "Approval changed concurrently. Reload before approving.")
        return approved

    async def export(self, project, testcase, version_id, format):
        state = await self.state(project, testcase)
        version = next((item for item in state["versions"] if item["version_id"] == version_id), None)
        if not version or version["status"] != "approved":
            raise HTTPException(409, "Select an approved natural-language design version to export.")
        snapshot = {key: version[key] for key in ("schema_version", "version_id", "case", "context", "content_digest", "approved_by", "approved_at", "stale")}
        snapshot.update({key: version[key] for key in ("approved_by_display_name", "approved_by_project_role", "approval_policy") if key in version})
        snapshot.update({"project_id": project, "testcase_id": testcase, "purpose": "manual-test-design", "executable": False})
        if format == "json":
            content, media = json.dumps(snapshot, ensure_ascii=False, indent=2), "application/json"
        else:
            case = version["case"]
            lines = [case["title"], "NATURAL-LANGUAGE TEST DESIGN — NOT AN AUTOMATION SCRIPT",
                f'Version: {version_id}', f'Approved by: {version.get("approved_by_display_name") or version["approved_by"]} (User {version["approved_by"]})', f'Approved at: {version["approved_at"]}', f'Review required for changed sources: {version["stale"]}',
                f'Purpose: {case["purpose"]}', f'Role: {case.get("role") or "Not specified"}', "", "Preconditions:",
                *["- " + item for item in case["preconditions"]], "", "Public data:",
                *[f"- {name}: {value}" for name, value in case["public_data"].items()], "", "Procedure:"]
            for index, step in enumerate(case["procedure"], 1):
                lines.extend([f'{index}. {step["instruction"]}', f'   Expected: {step["expected"]}'])
            lines.extend(["", "Required assertions:", *["- " + item for item in case["assertions"]], "", "Cleanup:",
                *["- " + item for item in case["cleanup"]], "", "Acceptance criteria:", *case["acceptance_criteria_refs"],
                "", "Rules:", *case["rule_references"], "", f'Knowledge version: {version["context"]["knowledge_version_id"]}',
                f'Story: {version["context"]["story_id"]}', f'Story analysis: {version["context"]["story_analysis_id"]}'])
            content, media = "\n".join(lines), "text/plain;charset=utf-8"
        return {"filename": f"{testcase}-{version_id}.{format if format == 'json' else 'txt'}", "media_type": media, "content": content}
