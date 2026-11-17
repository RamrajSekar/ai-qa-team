"""Pin existing story authority for design; never create another approval."""
from uuid import NAMESPACE_URL, uuid5
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from app.services.approved_visual_run import digest
from app.services.product_knowledge import ProductKnowledge
from app.utils.feature_flags import require_features


class ApprovedStoryContext:
    def __init__(self, database):
        self.db = database
        self.knowledge = ProductKnowledge(database)

    async def capture(self, project, story_id):
        require_features("product_knowledge", "story_analysis")
        from app.services.story_knowledge_review import StoryKnowledgeReview
        story = await self.knowledge.story(project, story_id)
        analysis = await self.knowledge.latest_analysis(project, story_id)
        knowledge = await self.knowledge.active(project)
        if not analysis:
            raise HTTPException(409, "Review and approve the story before generating scenarios.")
        raw = await self.knowledge.record("story_analyses", project, analysis["analysis_id"])
        if raw.get("story_digest") != digest(story):
            raise HTTPException(409, "Story changed. Review the updated story before generation.")
        reviews = StoryKnowledgeReview(self.db)
        explicit = (await reviews.review_states(project, [story])).get(story_id)
        changes = []
        if explicit and explicit["state"] == "approved":
            manifest = await reviews.row(project, story_id, explicit["review_id"])
            # A future release receipt alone does not activate its requirements.
            reconciled = await self.db["requirement_contexts"].find_one({
                "_id": "story_change_reconciled:" + explicit["review_id"], "project_id": project})
            if (not knowledge or knowledge["version_id"] != manifest["knowledge_version_id"]
                    or not reconciled or manifest["analysis_id"] != analysis["analysis_id"]
                    or manifest["analysis_digest"] != digest(raw)):
                raise HTTPException(409, "Knowledge changed or the approved change is not active. Review the current story context.")
            authority = {"kind": "story_change", **explicit, "content_digest": manifest["content_digest"]}
            changes = manifest["changes"]
        else:
            if raw.get("status") != "reviewed" or analysis["stale"]:
                raise HTTPException(409, "Review the current story context before generating scenarios.")
            authority = {"kind": "story_review", "analysis_id": analysis["analysis_id"],
                "approved_by": raw.get("reviewed_by"), "approved_by_name": raw.get("reviewed_by_name"),
                "approved_at": raw.get("reviewed_at"), "analysis_digest": digest(raw)}
        # Same-story proposals are excluded, never used to validate themselves.
        # A story-only review must not silently acquire knowledge validation.
        if raw.get("analysis_mode", "knowledge_aware") == "knowledge_aware" and knowledge:
            eligible, excluded = await self.knowledge.analysis_knowledge(project, story_id, knowledge)
            used = eligible["claims"]
        else:
            used, excluded = [], []
        basis = "approved_story_with_knowledge" if used else "approved_story_only"
        pinned = {"version_id": (knowledge or {}).get("version_id"), "claims": used,
                  "content_digest": digest(used)}
        context = {"knowledge": pinned, "analysis": self.knowledge.public(raw),
            "requirements_story": {**story,"acceptance_criteria":story.get("acceptance_criteria") or story.get("description") or ""}, "design_basis": basis,
            "criteria_basis": "approved_story_requirements", "target_release": "Current",
            "approved_requirement_changes": changes, "story_approval": authority,
            "independent_knowledge_validation": bool(used) and not excluded and not changes and not analysis["stale"], "excluded_knowledge_rules": excluded,
            "requirements_policy": "Generate within this approved story and scenario scope. Use only supplied independent approved rules and flows for prerequisites. Human-approved changes override the specifically superseded rules; do not infer unrelated changes. Story-only designs are not validated against product knowledge. Flag missing facts rather than inventing behavior."}
        # Pin the whole approved knowledge head even when all rules were excluded.
        fingerprint = digest({"story": story, "analysis": raw, "authority": authority,
            "knowledge_version": (knowledge or {}).get("version_id"),
            "knowledge_digest": (knowledge or {}).get("content_digest"), "context": context})
        identity = uuid5(NAMESPACE_URL, f"approved-story:{project}:{story_id}:{fingerprint}").hex
        return identity, fingerprint, context

    async def prepare(self, project, story):
        identity, fingerprint, context = await self.capture(project, story)
        document = {"_id": identity, "record_type": "approved_story_generation", "project_id": project,
            "story_id": story, "fingerprint": fingerprint, "context": context}
        document["content_digest"] = digest(document)
        try:
            await self.db["requirement_contexts"].insert_one(document)
        except DuplicateKeyError:
            pass
        return await self.resolve(project, story, identity)

    async def resolve(self, project, story, identity):
        row = await self.db["requirement_contexts"].find_one({"_id": identity, "project_id": project,
            "story_id": story, "record_type": "approved_story_generation"})
        if not row or digest({k: v for k, v in row.items() if k != "content_digest"}) != row.get("content_digest"):
            raise HTTPException(409, "Approved story context integrity check failed.")
        current_id, fingerprint, _ = await self.capture(project, story)
        if current_id != identity or fingerprint != row["fingerprint"]:
            raise HTTPException(409, "Approved story context changed. Review a successor design before continuing.")
        return {**row["context"], "requirements_context_id": identity,
                "requirements_context_digest": row["content_digest"]}
