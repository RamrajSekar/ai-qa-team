"""Explicit human story approval, separate from AI analysis and knowledge approval."""
from datetime import datetime, timezone
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from app.services.approved_visual_run import digest
from app.services.product_knowledge import ProductKnowledge
from app.utils.feature_flags import require_features


class ManualStoryReview:
    def __init__(self, database):
        self.db = database
        self.knowledge = ProductKnowledge(database)
        self.rows = database["requirement_contexts"]

    @staticmethod
    def snapshot_digest(story, analysis):
        return digest({"story": story, "analysis": analysis})

    @staticmethod
    def blocked(analysis):
        if not analysis:
            return False
        resolved = {r["finding_id"] for r in analysis.get("resolutions", [])} if analysis.get("status") == "reviewed" else set()
        return any((f["severity"] == "blocker" or f["category"] == "knowledge_conflict")
                   and f["finding_id"] not in resolved for f in analysis.get("findings", []))

    async def history_blocked(self,project,story):
        rows=await self.db["story_analyses"].find({"project_id":project,"story_id":story["story_id"],"story_digest":digest(story)}).to_list(1001)
        if len(rows)>1000:raise HTTPException(409,"Story review history exceeds the supported size.")
        return any(self.blocked(row) for row in rows)

    async def snapshot(self, project, story_id):
        require_features("product_knowledge", "story_analysis")
        story = await self.knowledge.story(project, story_id)
        analysis = await self.db["story_analyses"].find_one({"project_id": project, "story_id": story_id},
            sort=[("created_at", -1), ("_id", -1)])
        return story, analysis

    @staticmethod
    def verify(row):
        if digest({k: v for k, v in row.items() if k != "content_digest"}) != row.get("content_digest"):
            raise HTTPException(409, "Manual story approval integrity check failed.")
        return {"state": "approved", "basis": "manual_review", "approval_id": row["_id"],
            **{key: row[key] for key in ("approved_by", "approved_by_name", "approved_by_role", "approved_at", "policy", "note")},
            "content_digest": row["content_digest"]}

    async def current(self, project, story, analysis):
        fingerprint = self.snapshot_digest(story, analysis)
        row = await self.rows.find_one({"_id": "manual_story_approval:" + digest([project, story["story_id"], fingerprint]),
            "project_id": project, "story_id": story["story_id"], "record_type": "manual_story_approval"})
        if not row or self.blocked(analysis) or await self.history_blocked(project,story):
            return None
        if row["snapshot_digest"] != fingerprint:
            raise HTTPException(409, "Manual story approval snapshot mismatch.")
        return self.verify(row)

    async def summaries(self, project, stories, latest):
        keys={}
        for item in stories:
            story={k:item.get(k) for k in ("story_id","title","description","acceptance_criteria","out_of_scope")}
            key="manual_story_approval:"+digest([project,story["story_id"],self.snapshot_digest(story,latest.get(story["story_id"]))])
            keys[key]=story["story_id"]
        rows=await self.rows.find({"project_id":project,"record_type":"manual_story_approval","_id":{"$in":list(keys)}}).to_list(len(keys)) if keys else []
        return {keys[row["_id"]]:self.verify(row) for row in rows if not self.blocked(latest.get(keys[row["_id"]]))}

    async def readiness(self, project, story_id):
        story, analysis = await self.snapshot(project, story_id)
        return {"story": story, "snapshot_digest": self.snapshot_digest(story, analysis),
            "blocked": self.blocked(analysis) or await self.history_blocked(project,story), "approval": await self.current(project, story, analysis)}

    async def approve(self, project, story_id, actor, role, payload):
        if role!="ADMIN":raise HTTPException(403,"Project administrator access required")
        story, analysis = await self.snapshot(project, story_id)
        fingerprint = self.snapshot_digest(story, analysis)
        if fingerprint != payload.snapshot_digest:
            raise HTTPException(409, "Story or findings changed. Review the latest story before approval.")
        if self.blocked(analysis) or await self.history_blocked(project,story):
            raise HTTPException(409, "Resolve existing blockers and knowledge conflicts before manual approval.")
        row = {"_id": "manual_story_approval:" + digest([project, story_id, fingerprint]),
            "project_id": project, "story_id": story_id, "record_type": "manual_story_approval",
            "snapshot_digest": fingerprint, "story_digest": digest(story), "story_snapshot": story,
            "analysis_digest": digest(analysis), "basis": "manual_review", "note": payload.note.strip(),
            "approved_by": str(actor.get("_id") or actor.get("email")),
            "approved_by_name": actor.get("name") or actor.get("full_name") or "Project reviewer",
            "approved_by_role": role, "approved_at": datetime.now(timezone.utc).isoformat(),
            "policy": "project_admin_manual_story_review_v1"}
        row["content_digest"] = digest(row)
        try:
            await self.rows.insert_one(row)
        except DuplicateKeyError:
            pass  # First reviewer wins; repeated/concurrent calls never rewrite attribution.
        latest_story, latest_analysis = await self.snapshot(project, story_id)
        if self.snapshot_digest(latest_story, latest_analysis) != fingerprint:
            raise HTTPException(409, "Inputs changed during approval. Review the latest story.")
        result=await self.current(project, latest_story, latest_analysis)
        if not result:raise HTTPException(409,"Findings changed during approval. Review the latest story.")
        return result
