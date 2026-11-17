"""Human-approved story changes reuse the canonical knowledge successor/receipt path.

No model calls. A saved review is not an approval. Publication is one canonical
knowledge receipt; interrupted catalog marking can be explicitly reconciled.
"""
from datetime import datetime, timezone
import json
from uuid import NAMESPACE_URL, uuid5
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from app.models.product_knowledge import KnowledgeClaim, KnowledgeDraft
from app.services.approved_visual_run import digest
from app.services.product_knowledge import ProductKnowledge
from app.utils.feature_flags import require_features


class StoryKnowledgeReview:
    def __init__(self, database):
        self.db = database
        self.rows = database["requirement_contexts"]
        self.knowledge = ProductKnowledge(database)

    @staticmethod
    def identity(project, review, kind):
        return uuid5(NAMESPACE_URL, f"story-knowledge:{project}:{review}:{kind}").hex

    async def row(self, project, story, identity):
        require_features("product_knowledge", "story_analysis")
        row = await self.rows.find_one({"_id": identity, "project_id": project,
            "story_id": story, "record_type": "story_knowledge_review"})
        if not row:
            raise HTTPException(404, "Story change review not found.")
        if digest({k: v for k, v in row.items() if k != "content_digest"}) != row["content_digest"]:
            raise HTTPException(409, "Saved review integrity check failed.")
        return row

    async def fresh(self, row, current=None):
        if current is None:
            story = await self.knowledge.story(row["project_id"], row["story_id"])
            active = await self.knowledge.active(row["project_id"])
            analysis = await self.knowledge.latest_analysis(row["project_id"], row["story_id"])
            raw = await self.knowledge.record("story_analyses", row["project_id"], analysis["analysis_id"]) if analysis else None
        else:
            story, active, analysis, raw = current
        if (digest(story) != row["story_digest"] or not active
                or active["version_id"] != row["parent_version_id"]
                or active["content_digest"] != row["parent_digest"]
                or not analysis or analysis["analysis_id"] != row["analysis_id"] or analysis["stale"]):
            raise HTTPException(409, "Story or knowledge changed. Review the updated comparison and submit a new review.")
        if digest(raw) != row["analysis_digest"]:
            raise HTTPException(409, "Analysis review changed. Submit a new review.")

    async def approval(self, row):
        return await self.rows.find_one({"_id": "story_change_approval:" + row["review_id"],
            "project_id": row["project_id"], "content_digest": row["content_digest"]})

    async def view(self, row, current=None):
        approval = await self.approval(row)
        published = await self.db["product_knowledge_versions"].find_one({
            "project_id": row["project_id"], "_id": row["knowledge_version_id"]})
        published = await self.knowledge.approved_view(row["project_id"], published) if published else None
        complete = await self.rows.find_one({"_id": "story_change_reconciled:" + row["review_id"],
            "project_id": row["project_id"]})
        try:
            await self.fresh(row, current)
            stale = False
        except HTTPException as error:
            if error.status_code != 409:
                raise
            stale = True
        status = ("completed" if complete else "reconciling") if published and published["status"] == "approved" else (
            "approved_pending" if approval else "submitted")
        fields = ("review_id", "analysis_id", "parent_version_id", "knowledge_version_id", "timing",
            "target_release", "decisions", "changes", "impact", "submitted_by", "created_at")
        return {**{key: row[key] for key in fields}, "status": status, "stale": stale,
            "approver": {key: approval[key] for key in ("approved_by", "approved_by_name", "approved_by_role", "approved_at")} if approval else None}

    async def listing(self, project, story):
        require_features("product_knowledge", "story_analysis")
        story_data = await self.knowledge.story(project, story)
        active = await self.knowledge.active(project)
        analysis = await self.knowledge.latest_analysis(project, story)
        raw = await self.knowledge.record("story_analyses", project, analysis["analysis_id"]) if analysis else None
        rows = await self.rows.find({"project_id": project, "story_id": story,
            "record_type": "story_knowledge_review"}).sort("created_at", -1).to_list(50)
        return {"knowledge_version_id": (active or {}).get("version_id"),
            "rules": [{"claim_id": c["claim_id"], "statement": c["statement"]} for c in (active or {}).get("claims", [])],
            "reviews": [await self.view(await self.row(project, story, r["review_id"]), (story_data, active, analysis, raw)) for r in rows]}

    async def submit(self, project, story_id, actor, payload):
        require_features("product_knowledge", "story_analysis")
        existing = await self.rows.find_one({"_id": payload.request_id})
        request_digest = digest(payload.model_dump())
        if existing:
            row = await self.row(project, story_id, payload.request_id)
            if row["request_digest"] != request_digest:
                raise HTTPException(409, "Save identity already used. Review the saved submission.")
            return await self.view(row)
        story = await self.knowledge.story(project, story_id)
        active = await self.knowledge.active(project)
        analysis = await self.knowledge.latest_analysis(project, story_id)
        if (not active or active["version_id"] != payload.parent_version_id or not analysis
                or analysis["analysis_id"] != payload.analysis_id or analysis["stale"]):
            raise HTTPException(409, "Compare the current story with approved knowledge before submitting a change.")
        findings = {f["finding_id"]: f for f in analysis["findings"]}
        decisions = [d.model_dump() for d in payload.decisions]
        selected = [d["finding_id"] for d in decisions]
        conflicts = {key for key, f in findings.items() if f["category"] == "knowledge_conflict"}
        if (len(selected) != len(set(selected)) or not conflicts.issubset(selected) or set(selected) - findings.keys()
                or (not conflicts and analysis.get("status") != "reviewed")):
            raise HTTPException(422, "Review the story and record a decision for every knowledge conflict.")
        rules = {c["claim_id"]: c for c in active["claims"]}
        targeted = []
        for decision in decisions:
            finding = findings[decision["finding_id"]]
            if decision["decision"] == "intentional_change":
                rule = decision["rule_id"]
                if decision["finding_id"] not in conflicts:
                    if decision["action"] != "add" or rule is not None:
                        raise HTTPException(422,"A reviewed non-conflict finding may propose a new rule only. Use conflict review to change existing rules.")
                    continue
                if decision["action"] not in ("replace", "remove") or rule not in rules or rule != finding.get("knowledge_claim_id"):
                    raise HTTPException(422, "Review the exact existing rule linked to each conflict.")
                targeted.append(rule)
        if len(targeted) != len(set(targeted)):
            raise HTTPException(422, "Combine changes targeting the same rule before submission.")
        resolutions = [r.model_dump() for r in payload.resolutions]
        resolved = {r["finding_id"] for r in resolutions}
        if len(resolved) != len(resolutions) or resolved & conflicts or resolved - findings.keys() or any(not r["rationale"].strip() for r in resolutions):
            raise HTTPException(422, "Review other findings separately with a meaningful explanation.")
        required = {key for key, f in findings.items() if f["severity"] == "blocker"} - set(selected)
        if not required.issubset(resolved):
            raise HTTPException(422, "Resolve the other blocking findings before submitting approval.")
        changes = [{"action": d["action"], "rule_id": d["rule_id"] or "K_"+self.identity(project,payload.request_id,str(index)), "category": rules[d["rule_id"]]["category"] if d["rule_id"] else "business_rule",
            "before": rules[d["rule_id"]]["statement"] if d["rule_id"] else None,
            "after": None if d["action"] == "remove" else d["expected_result"],
            "expected_behavior": d["expected_result"], "reason": d["rationale"]}
            for index,d in enumerate(decisions) if d["decision"] == "intentional_change"]
        impact = {}
        for collection, key in (("scenarios", "scenario_id"), ("testcases", "testcase_id")):
            items = await self.db[collection].find({"project_id": project}).to_list(1001)
            if len(items) > 1000:
                raise HTTPException(409, "Impact review exceeds supported bounds.")
            impact[collection] = [{"id": item[key], "title": item.get("title", "")} for item in items
                if item.get("knowledge_version_id") == active["version_id"] or set(item.get("rule_references") or []) & set(targeted)]
        row = {"_id": payload.request_id, "review_id": payload.request_id, "record_type": "story_knowledge_review",
            "project_id": project, "story_id": story_id, "story_snapshot": story, "story_digest": digest(story),
            "analysis_id": payload.analysis_id,
            "analysis_digest": digest(await self.knowledge.record("story_analyses", project, payload.analysis_id)),
            "parent_version_id": active["version_id"], "parent_digest": active["content_digest"],
            "timing": payload.timing, "target_release": payload.target_release.strip(), "decisions": decisions,
            "resolutions": resolutions, "changes": changes, "impact": impact, "request_digest": request_digest,
            "source_id": self.identity(project, payload.request_id, "source"),
            "knowledge_version_id": self.identity(project, payload.request_id, "version"),
            "submitted_by": actor, "created_at": datetime.now(timezone.utc).isoformat()}
        row["content_digest"] = digest(row)
        if len(json.dumps(row).encode()) > 250000 or len("\n\n".join(c["expected_behavior"] for c in changes)) > 60000:
            raise HTTPException(413, "Keep the reviewed changes within supported knowledge bounds.")
        try:
            await self.rows.insert_one(row)
        except DuplicateKeyError:
            return await self.submit(project, story_id, actor, payload)
        return await self.view(row)

    async def approve(self, project, story, identity, user, *, activate=False):
        row = await self.row(project, story, identity)
        if any(d["decision"] != "intentional_change" for d in row["decisions"]):
            raise HTTPException(409, "Correct the story or clarify the pending decisions before approval.")
        approval = await self.approval(row)
        if activate and (row["timing"] != "later" or not approval):
            raise HTTPException(409, "Approve the future change before activation.")
        if not approval:
            await self.fresh(row)
            approval = {"_id": "story_change_approval:" + identity, "project_id": project,
                "record_type": "story_change_approval", "content_digest": row["content_digest"],
                "approved_by": str(user.get("_id") or user.get("email")),
                "approved_by_name": user.get("name") or user.get("email") or "Project administrator",
                "approved_by_role": "ADMIN", "approved_at": datetime.now(timezone.utc).isoformat()}
            try:
                await self.rows.insert_one(approval)
            except DuplicateKeyError:
                approval = await self.approval(row)
                if not approval:
                    raise HTTPException(409, "Approval changed. Reload the review.") from None
        if row["timing"] == "later" and not activate:
            return await self.view(row)
        return await self.publish(row, approval, user)

    async def publish(self, row, approval, user):
        project, identity = row["project_id"], row["review_id"]
        version = await self.db["product_knowledge_versions"].find_one({"project_id": project, "_id": row["knowledge_version_id"]})
        approved = await self.knowledge.approved_view(project, version) if version else None
        if not approved or approved["status"] != "approved":
            await self.fresh(row)
            text = "\n\n".join(c["expected_behavior"] for c in row["changes"])
            source = {"_id": row["source_id"], "source_id": row["source_id"], "project_id": project,
                "kind": "document", "title": "Approved requirement change from " + row["story_id"],
                "text": text, "segments": [], "origin": {"kind": "story", "story_id": row["story_id"],
                    "review_id": identity, "story_digest": row["story_digest"], "human_approved_change": True},
                "created_by": approval["approved_by"], "created_at": approval["approved_at"]}
            try:
                await self.db["product_knowledge_sources"].insert_one(source)
            except DuplicateKeyError:
                existing = await self.knowledge.record("product_knowledge_sources", project, row["source_id"])
                if existing["text"] != text or existing.get("origin") != source["origin"]:
                    raise HTTPException(409, "Saved change source differs. Reload the review.") from None
            claims = [KnowledgeClaim(claim_id=c["rule_id"], category=c["category"], statement=c["after"],
                epistemic_status="expected", source_id=row["source_id"], quote=c["expected_behavior"][:1200])
                for c in row["changes"] if c["action"] != "remove"]
            removed = [c["rule_id"] for c in row["changes"] if c["action"] == "remove"]
            draft = KnowledgeDraft(title="Approved story change: " + row["story_id"], claims=claims,
                parent_version_id=row["parent_version_id"], removed_claim_ids=removed,
                removal_reasons={c["rule_id"]: c["reason"] for c in row["changes"] if c["action"] == "remove"})
            await self.knowledge.create_version(project, approval["approved_by"], draft, version_id=row["knowledge_version_id"])
            await self.knowledge.approve(project, approval["approved_by"], row["knowledge_version_id"], actor_name=approval["approved_by_name"])
        # Knowledge receipt is authoritative even if this response or marking fails.
        done = "story_change_reconciled:" + identity
        if not await self.rows.find_one({"_id": done, "project_id": project}):
            try:
                for collection, items in row["impact"].items():
                    key = "scenario_id" if collection == "scenarios" else "testcase_id"
                    for item in items:
                        await self.db[collection].update_one({"project_id": project, key: item["id"]}, {"$set": {
                            "requirements_review_required": True, "requirements_review_context_id": identity,
                            "requirements_review_release": row["target_release"],
                            "requirements_reviews." + identity: {"context_id": identity, "release": row["target_release"]}}})
                await self.rows.insert_one({"_id": done, "project_id": project, "record_type": "story_change_reconciled",
                    "activated_by": str(user.get("_id") or user.get("email")), "activated_at": datetime.now(timezone.utc).isoformat()})
            except DuplicateKeyError:
                pass
            except Exception:
                raise HTTPException(503, "Knowledge was updated. Explicitly retry this same approval to finish marking affected designs; do not submit it again.") from None
        return await self.view(row)
