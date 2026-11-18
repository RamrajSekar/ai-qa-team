"""Read-only overview queue; original services remain approval authority."""
import asyncio
from urllib.parse import quote
from fastapi import HTTPException
from app.config import settings
from app.services.product_knowledge import ProductKnowledge
from app.services.test_design_review import TestDesignReview
from app.services.story_knowledge_review import StoryKnowledgeReview


class PendingProjectReviews:
    def __init__(self, database):
        self.db = database
        self.knowledge = ProductKnowledge(database)

    async def listing(self, project, page=0, limit=20, *, project_record=None):
        root = "/projects/" + quote(project, safe="")
        project_record=project_record or await self.db["projects"].find_one({"project_id":project}) or {}
        memberships=await self.db["project_memberships"].find({"project_id":project,"status":"ACTIVE"}).to_list(201)
        if len(memberships)>200:raise HTTPException(409,"Reviewer list exceeds the supported size.")
        emails={m["email"].strip().lower():m for m in memberships}
        scope={"email":{"$in":list(emails)}}
        if project_record.get("account_id"):scope.update(account_id=project_record["account_id"],account_state="ACTIVE")
        profiles=await self.db["users"].find(scope,{"email":1,"name":1,"full_name":1}).to_list(200) if emails else []
        names={u["email"].strip().lower():u.get("name") or u.get("full_name") or "Unnamed reviewer" for u in profiles}
        def reviewers(kind,owner=None):
            if kind=="Scenario":eligible=[owner.strip().lower()] if owner else []
            elif kind=="Test Case" and not settings.features.test_design_admin_review:eligible=list(emails)
            else:eligible=[email for email,m in emails.items() if m.get("role")=="ADMIN"]
            return sorted({names[email] for email in eligible if email in names})
        rows, errors, more = [], [], []
        slots = asyncio.Semaphore(4)

        async def source(collection, identity, extra=None):
            values = await self.db[collection].find({"project_id": project, **(extra or {})}).sort(identity, 1).skip(page * limit).limit(limit + 1).to_list(limit + 1)
            more.append(len(values) > limit)
            return values[:limit]

        def add(kind, identity, title, state, href, detail="", owner=None):
            rows.append({"type": kind, "id": identity, "title": title, "status": state,
                         "href": href, "detail": detail,"pending_with":reviewers(kind,owner),"reviewer_basis":"eligible_reviewers"})

        async def bounded(function, item):
            async with slots:
                await function(item)

        async def hydrate(function,values):
            results=await asyncio.gather(*(bounded(function,item) for item in values),return_exceptions=True)
            for result in results:
                if isinstance(result,BaseException):raise result

        async def stories():
            values = await source("stories", "story_id")
            summaries = await self.knowledge.analysis_summaries(project, [s["story_id"] for s in values]) if values else {}
            for item in values:
                summary = summaries[item["story_id"]]
                if summary["story_approval"]["state"] == "approved":
                    continue
                add("Story", item["story_id"], item["title"], "Needs review" if summary["state"] == "stale" else "In review",
                    root + "/stories/" + quote(item["story_id"], safe="") + "#story-analysis",
                    "Resolve findings or review manually." if summary["state"] != "stale" else "Story or analysis context changed.")

        async def scenarios():
            values = await source("scenarios", "scenario_id")
            async def present(item):
                pending = not item.get("approved") or item.get("requirements_review_required")
                detail = ""
                if item.get("approved") and (item.get("requirements_context_id") or item.get("knowledge_version_id")):
                    try:
                        context=await self.knowledge.generation_context(project, item["story_id"], item.get("requirements_context_id"))
                        if (item.get("knowledge_version_id")!=context["knowledge"]["version_id"] or item.get("story_analysis_id")!=context["analysis"]["analysis_id"] or item.get("requirements_context_digest")!=context.get("requirements_context_digest")):
                            pending=True;detail="Approved source context changed."
                    except HTTPException as failure:
                        if failure.status_code not in (404, 409): raise
                        pending = True
                        detail = str(failure.detail)
                if pending:
                    add("Scenario", item["scenario_id"], item["title"], "Needs review" if item.get("approved") else "In review",
                        root + "/scenarios?review=" + quote(item["scenario_id"], safe=""), detail,owner=item.get("created_by"))
            await hydrate(present,values)

        async def cases():
            values = await source("testcases", "testcase_id")
            async def present(item):
                state = await TestDesignReview(self.db).state(project, item["testcase_id"])
                if state["review_required"] or item.get("requirements_review_required"):
                    add("Test Case", item["testcase_id"], item["title"], "Blocked" if not state["context_ready"] else "Needs review" if state["active_version_id"] else "In review",
                        root + "/testcases?review=" + quote(item["testcase_id"], safe=""), state["context_error"] or "")
            await hydrate(present,values)

        async def training():
            values = await source("knowledge_training_reviews", "review_id")
            ids = [r["draft_version_id"] for r in values if r["state"] in ("saving", "saved")]
            documents = await self.db["product_knowledge_versions"].find({"project_id": project, "_id": {"$in": ids}}).to_list(len(ids)) if ids else []
            approved = {v["version_id"]: v for v in await self.knowledge.approved_views(project, documents)}
            for item in values:
                if item["state"] == "rejected" or approved.get(item["draft_version_id"], {}).get("status") == "approved": continue
                state = "Awaiting approval" if item["state"] in ("saving", "saved") else "Needs attention" if item["extraction_state"] in ("uncertain", "running") else "In review"
                add("Knowledge", item["review_id"], item["title"], state,
                    root + "/knowledge?review=" + quote(item["review_id"], safe=""), "Training review")

        async def changes():
            values = await source("requirement_contexts", "review_id", {"record_type": "story_knowledge_review"})
            service = StoryKnowledgeReview(self.db)
            async def present(item):
                saved = await service.view(await service.row(project, item["story_id"], item["review_id"]))
                if saved["status"] == "completed": return
                state = "Needs review" if saved["stale"] else "Awaiting activation" if saved["status"] == "approved_pending" else "Needs attention" if saved["status"] == "reconciling" else "Awaiting approval"
                add("Knowledge", item["review_id"], "Knowledge change from " + item["story_id"], state,
                    root + "/stories/" + quote(item["story_id"], safe="") + "#story-analysis", "Review the proposed knowledge changes.")
            await hydrate(present,values)

        tasks = []
        flags = settings.features
        if flags.product_knowledge and flags.story_analysis and flags.story_management: tasks.append(("Stories", stories))
        if flags.scenario_generation and flags.story_management: tasks.append(("Scenarios", scenarios))
        if flags.test_generation: tasks.append(("Test Cases", cases))
        if flags.product_knowledge: tasks.append(("Knowledge training", training))
        if flags.product_knowledge and flags.story_analysis: tasks.append(("Knowledge changes", changes))
        # Isolate type failures so one unavailable context does not erase other rows.
        async def collect(name, function):
            try: await function()
            except Exception:
                errors.append(name)
        await asyncio.gather(*(collect(name, function) for name, function in tasks))
        rows.sort(key=lambda r: (r["type"], r["id"]))
        return {"items": rows, "page": page, "page_size": limit, "has_more": any(more), "unavailable_types": sorted(errors)}
