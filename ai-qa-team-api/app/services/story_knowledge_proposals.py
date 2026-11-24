"""Faithful approved-story copies into the existing knowledge review pipeline. No AI."""
from uuid import NAMESPACE_URL, uuid5
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from app.models.product_knowledge import KnowledgeClaim, KnowledgeSourceInput
from app.services.product_knowledge import ProductKnowledge
from app.services.knowledge_training import KnowledgeTraining, now
from app.services.manual_story_review import ManualStoryReview
from app.services.story_knowledge_review import StoryKnowledgeReview
from app.services.approved_visual_run import digest
from app.utils.feature_flags import require_features


class StoryKnowledgeProposals:
    def __init__(self, database):
        self.db = database
        self.knowledge = ProductKnowledge(database)
        self.training = KnowledgeTraining(database, self.knowledge)

    @staticmethod
    def identity(project, value):
        return uuid5(NAMESPACE_URL, f"approved-story-knowledge:{project}:{value}").hex

    async def approved_source(self, project, story_id):
        require_features("product_knowledge", "story_analysis")
        story = await self.knowledge.story(project, story_id)
        raw = await self.db["story_analyses"].find_one({"project_id": project, "story_id": story_id}, sort=[("created_at", -1), ("_id", -1)])
        manual = await ManualStoryReview(self.db).current(project, story, raw)
        changes = []
        if manual:
            authority = {"kind": "manual_review", **manual}
        else:
            service = StoryKnowledgeReview(self.db)
            explicit = (await service.review_states(project, [story])).get(story_id)
            if explicit and explicit["state"] == "approved":
                manifest = await service.row(project, story_id, explicit["review_id"])
                view = await service.view(manifest)
                if view["status"] != "completed" or not view["story_matches"]:
                    raise HTTPException(409, "Complete the approved story change before proposing knowledge.")
                raw = await self.knowledge.record("story_analyses", project, manifest["analysis_id"])
                if digest(raw) != manifest["analysis_digest"]:
                    raise HTTPException(409, "The approved story review changed. Review current inputs.")
                authority = {"kind": "story_change", **explicit, "content_digest": manifest["content_digest"]}
                changes = manifest["changes"]
            elif raw and raw.get("status") == "reviewed" and raw.get("story_digest") == digest(story):
                authority = {"kind": "story_review", "analysis_id": raw["analysis_id"], "analysis_digest": digest(raw),
                    "approved_by": raw.get("reviewed_by"), "approved_by_name": raw.get("reviewed_by_name"), "approved_at": raw.get("reviewed_at")}
            else:
                raise HTTPException(409, "Approve the current story before adding or updating knowledge.")
        clarifications = [r["rationale"] for r in (raw or {}).get("resolutions", []) if r["decision"] == "clarified"] if not manual else []
        text = "\n\n".join(f"{label}:\n{value}" for label, value in (
            ("Title", story["title"]), ("Description", story["description"]), ("Acceptance criteria", story["acceptance_criteria"]),
            ("Out of scope", story["out_of_scope"]), ("Reviewed clarifications", "\n\n".join(clarifications)),
            ("Approved changes", "\n\n".join(c["expected_behavior"] for c in changes))) if value)
        primary = [c["expected_behavior"] for c in changes] if changes else [story["acceptance_criteria"] if (story["acceptance_criteria"] or "").strip() else story["description"]]
        requirements = [*primary, *clarifications]
        # Description may contain business intent absent from acceptance criteria.
        # Keep it in Add drafts; focused corrections use the primary requirements.
        fragments = {"add": ([story["description"]] if not changes and (story["description"] or "").strip() else []) + requirements,
                     "update": requirements}
        fingerprint = digest({"story": story, "authority": authority, "text": text})
        return story, text, fragments, fingerprint

    async def ensure_fresh(self, project, origin):
        if origin.get("approved_story_copy"):
            _, _, _, fingerprint = await self.approved_source(project, origin["story_id"])
            if fingerprint != origin["approved_source_digest"]:
                raise HTTPException(409, "The approved story changed. Create a knowledge proposal from the current approved story.")

    async def options(self, project, story):
        await self.approved_source(project, story)
        active = await self.knowledge.active(project)
        claims = (active or {}).get("claims", [])
        source_ids = list({c["source_id"] for c in claims})
        sources = await self.db["product_knowledge_sources"].find({"project_id": project, "source_id": {"$in": source_ids}}).to_list(100) if source_ids else []
        linked = {s["source_id"] for s in sources if s.get("origin", {}).get("story_id") == story}
        pending = await self.training.rows.find({"project_id": project, "source_origin.story_id": story,
            "state": {"$ne": "rejected"}}).sort("created_at", -1).to_list(51)
        if len(pending) > 50:
            raise HTTPException(409, "Review existing knowledge requests in QA Agent first.")
        review_id = None
        for row in pending:
            view = await self.training.get(project, row["review_id"])
            if (view.get("saved_version") or {}).get("status") != "approved":
                review_id = row["review_id"]
                break
        return {"version_id": (active or {}).get("version_id"), "rules": [
            {"claim_id": c["claim_id"], "statement": c["statement"]} for c in claims if c["source_id"] in linked],
            "pending_review_id": review_id}

    @staticmethod
    def chunks(text):
        # Preserve every character of a long requirement across bounded excerpts.
        while text:
            end = min(len(text), 1200)
            if end < len(text):
                boundary = max(text.rfind("\n", 0, end), text.rfind(" ", 0, end))
                if boundary > 0: end = boundary
            part = text[:end].strip()
            if part: yield part
            text = text[end:].lstrip()

    async def start(self, project, story_id, actor, payload):
        story, _, _, fingerprint = await self.approved_source(project, story_id)
        identity = self.identity(project, digest([story_id, fingerprint, payload.change_type, payload.claim_id]))
        existing = await self.training.rows.find_one({"_id": self.training.key(project, identity), "project_id": project})
        if existing:
            if existing["state"] == "rejected":
                raise HTTPException(409, "This proposal was discarded. Start intentional new training in QA Agent.")
            return await self.training.get(project, identity)
        if payload.change_type == "add":
            options = await self.options(project, story_id)
            if options["pending_review_id"]:
                return await self.training.get(project, options["pending_review_id"])
            if options["rules"]:
                raise HTTPException(409, "This story already has approved knowledge. Update its knowledge instead.")
        active = await self.knowledge.active(project)
        selected = None
        if payload.change_type == "update":
            if not active or active["version_id"] != payload.base_version_id:
                raise HTTPException(409, "Approved knowledge changed. Select the current rule again.")
            selected = next((c for c in active["claims"] if c["claim_id"] == payload.claim_id), None)
            if not selected: raise HTTPException(409, "Select a rule from current approved knowledge.")
        source_id = self.identity(project, identity + ":source")
        draft_id = self.identity(project, identity + ":draft")
        # A story contributes one literal criteria entry, never review commentary.
        statement = (story.get("acceptance_criteria") or "").strip()
        if not statement:
            raise HTTPException(409, "Add acceptance criteria to the story before proposing knowledge.")
        if len(statement) > 1500:
            raise HTTPException(413, "A single knowledge entry supports 1500 characters. Shorten the story criteria or use QA Agent for a larger source.")
        text = f"Title:\n{story['title']}\n\nAcceptance criteria:\n{statement}"
        if len(text)>60000:raise HTTPException(413,"Keep the complete story source within 60000 characters.")
        source = KnowledgeSourceInput(title=("Story: " + story["title"])[:240], kind="document", text=text)
        origin = {"kind": "story", "story_id": story_id, "story_digest": digest(story), "training_review_id": identity,
                  "approved_story_copy": True, "approved_source_digest": fingerprint}
        statements = [statement]
        proposals = [{"claim": KnowledgeClaim(claim_id=selected["claim_id"] if selected else "K_"+self.identity(project,identity+":"+str(index)),
            category=selected["category"] if selected else "business_rule", statement=statement, epistemic_status="expected",
            source_id=source_id, quote=statement[:1200]).model_dump(), "decision": "pending"} for index, statement in enumerate(statements)]
        if not selected and {p["claim"]["claim_id"] for p in proposals}&{c["claim_id"] for c in (active or {}).get("claims",[])}:
            raise HTTPException(409,"An addition cannot replace an existing knowledge rule.")
        timestamp = now()
        document = {**source.model_dump(), "_id": source_id, "source_id": source_id, "project_id": project,
                    "origin": origin, "created_by": actor, "created_at": timestamp}
        try: await self.db["product_knowledge_sources"].insert_one(document)
        except DuplicateKeyError:
            previous = await self.knowledge.record("product_knowledge_sources", project, source_id)
            if previous["text"] != text or previous.get("origin") != origin:
                raise HTTPException(409, "Story source identity has different content.") from None
        await self.ensure_fresh(project, origin)
        row = {"_id": self.training.key(project, identity), "review_id": identity, "project_id": project,
            "title": (("Update knowledge: " if selected else "Knowledge from story: ")+story["title"])[:240],
            "mode": "correction" if selected else "training", "input_digest": digest([fingerprint, payload.model_dump()]),
            "source_input": None, "source_origin": origin, "source_id": source_id, "base_version_id": (active or {}).get("version_id"),
            "state": "reviewing", "extraction_state": "completed", "attempt": 0, "revision": 0, "proposals": proposals,
            "clarification_questions": [], "clarification_answers": {}, "removed_claim_ids": [], "draft_version_id": draft_id,
            "created_by": actor, "created_at": timestamp, "updated_at": timestamp}
        try: await self.training.rows.insert_one(row)
        except DuplicateKeyError: pass
        return await self.training.get(project, identity)
