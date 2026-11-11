"""Versioned reusable workflows and test specifications; no browser dispatch."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pymongo import ReturnDocument

from app.config import settings
from app.services.product_knowledge import ProductKnowledge
from app.models.visual_specification import VisualStep, CompiledSpecificationPreview
from app.services.approved_visual_run import ApprovedVisualRuns, digest
from app.services.staging_run_binding import sandbox_url
from app.utils.feature_flags import require_features


class VisualSpecifications:
    def __init__(self, db, digest_key):
        self.db = db
        self.digest_key = digest_key
        self.sources = ApprovedVisualRuns(db, digest_key)

    @staticmethod
    def public(document):
        return {key: value for key, value in document.items() if key != "_id"}

    async def version(self, collection, project, version_id):
        require_features("reusable_workflows")
        document = await self.db[collection].find_one({"project_id": project, "_id": version_id})
        if not document:
            raise HTTPException(404, "Version not found in this project.")
        if document.get("schema_version", "1.0") != "1.0":
            raise HTTPException(409, "This specification schema version is not supported.")
        return document

    async def active(self, collection, project, key, identity):
        return await self.db[collection].find_one(
            {"project_id": project, key: identity, "status": "approved"},
            sort=[("approved_at", -1), ("_id", -1)],
        )

    async def workflows(self, project):
        require_features("reusable_workflows")
        documents = await self.db["visual_workflow_versions"].find({"project_id": project}).sort("created_at", -1).to_list(100)
        return [self.public(document) for document in documents]

    async def create_workflow(self, project, actor, payload):
        require_features("reusable_workflows")
        if any(step.action == "reusable" for step in payload.steps):
            raise HTTPException(422, "Nested reusable workflows are not supported.")
        workflow_id = payload.workflow_id or "WF_" + uuid4().hex
        if payload.workflow_id and not await self.db["visual_workflow_versions"].find_one({"project_id": project, "workflow_id": workflow_id}):
            raise HTTPException(404, "Workflow not found in this project.")
        parameters = sorted({step.value.name for step in payload.steps if step.value and step.value.source == "parameter"})
        return await self.insert("visual_workflow_versions", project, actor, {
            "workflow_id": workflow_id, "title": payload.title, "steps": [step.model_dump(exclude_none=True) for step in payload.steps],
            "parameters": parameters,
        })

    async def insert(self, collection, project, actor, fields):
        version_id = uuid4().hex
        document = {**fields, "schema_version": "1.0", "_id": version_id, "version_id": version_id, "project_id": project,
                    "status": "draft", "created_by": actor, "created_at": datetime.now(timezone.utc).isoformat(),
                    "content_digest": digest({"schema_version": "1.0", **fields})}
        await self.db[collection].insert_one(document)
        return self.public(document)

    async def approve_workflow(self, project, actor, version_id):
        document = await self.version("visual_workflow_versions", project, version_id)
        if not any(step["action"] == "assert_text" for step in document["steps"]):
            raise HTTPException(409, "Add an explicit expected result before workflow approval.")
        return await self.approve("visual_workflow_versions", document, actor, {})

    async def approve(self, collection, document, actor, fields):
        if document["status"] == "approved":
            return self.public(document)
        updated = await self.db[collection].find_one_and_update(
            {"_id": document["_id"], "project_id": document["project_id"], "status": "draft"},
            {"$set": {**fields, "status": "approved", "approved_by": actor,
                      "approved_at": datetime.now(timezone.utc).isoformat()}}, return_document=ReturnDocument.AFTER,
        )
        return self.public(updated or await self.version(collection, document["project_id"], document["_id"]))

    async def compile(self, project, steps):
        actions, references = [], []
        for raw in steps:
            step = VisualStep.model_validate(raw)
            if step.action != "reusable":
                if step.value and step.value.source == "parameter":
                    raise HTTPException(422, "Parameters must be bound through a reusable workflow call.")
                actions.append(step.model_dump(exclude_none=True))
                continue
            workflow = await self.version("visual_workflow_versions", project, step.workflow_version_id)
            active = await self.active("visual_workflow_versions", project, "workflow_id", workflow["workflow_id"])
            if workflow["status"] != "approved" or not active or active["version_id"] != workflow["version_id"]:
                raise HTTPException(409, "A reusable workflow changed or needs approval. Review and select its current approved version.")
            if set(step.inputs) != set(workflow["parameters"]):
                raise HTTPException(422, "Supply exactly the required reusable workflow inputs.")
            for action in workflow["steps"]:
                action = dict(action)
                if action.get("value", {}).get("source") == "parameter":
                    action["value"] = step.inputs[action["value"]["name"]].model_dump(exclude_none=True)
                actions.append(action)
            references.append({"workflow_id": workflow["workflow_id"], "version_id": workflow["version_id"],
                               "content_digest": workflow["content_digest"]})
        if len(actions) > 40:
            raise HTTPException(422, "Expanded specifications are limited to 40 steps.")
        return actions, references

    async def create_specification(self, project, testcase, actor, payload):
        require_features("reusable_workflows")
        story, scenario, criteria, source = await self.sources.source(project, testcase)
        steps = [step.model_dump(exclude_none=True) for step in payload.steps]
        await self.compile(project, steps)
        knowledge_pin = {}
        if settings.features.product_knowledge:
            context = await ProductKnowledge(self.db).generation_context(project, story)
            knowledge_pin = {"knowledge_version_id": context["knowledge"]["version_id"],
                             "knowledge_content_digest": context["knowledge"]["content_digest"],
                             "story_analysis_id": context["analysis"]["analysis_id"]}
        return await self.insert("visual_test_spec_versions", project, actor, {
            "testcase_id": testcase, "story_id": story, "scenario_id": scenario,
            "source_digest": source, "acceptance_criteria_snapshot": criteria, "steps": steps, **knowledge_pin,
        })

    async def validate_specification(self, project, document):
        _, _, _, source = await self.sources.source(project, document["testcase_id"])
        if source != document["source_digest"]:
            raise HTTPException(409, "Story, scenario or test case changed. Create and review a successor specification.")
        if settings.features.product_knowledge:
            context = await ProductKnowledge(self.db).generation_context(project, document["story_id"])
            if (document.get("knowledge_version_id") != context["knowledge"]["version_id"]
                    or document.get("story_analysis_id") != context["analysis"]["analysis_id"]):
                raise HTTPException(409, "Approved knowledge or story analysis changed. Review a successor specification.")
        return await self.compile(project, document["steps"])

    async def approve_specification(self, project, testcase, actor, version_id):
        document = await self.version("visual_test_spec_versions", project, version_id)
        if document["testcase_id"] != testcase:
            raise HTTPException(404, "Specification not found for this test case.")
        actions, references = await self.validate_specification(project, document)
        if not any(step["action"] == "assert_text" for step in actions):
            raise HTTPException(409, "An explicit expected result is required before approval.")
        return await self.approve("visual_test_spec_versions", document, actor,
                                  {"compiled_steps": actions, "workflow_versions": references})

    async def latest_specification(self, project, testcase):
        require_features("reusable_workflows")
        document = await self.db["visual_test_spec_versions"].find_one(
            {"project_id": project, "testcase_id": testcase}, sort=[("created_at", -1), ("_id", -1)])
        if not document:
            return {"version": None, "review_required": False, "reason": None}
        try:
            await self.validate_specification(project, document)
        except HTTPException as exc:
            if exc.status_code not in (404, 409, 422):
                raise
            return {"version": self.public(document), "review_required": True,
                    "reason": "Source or reusable workflow changed. Review a successor specification."}
        return {"version": self.public(document), "review_required": document["status"] != "approved", "reason": None}

    async def preview(self, project, testcase, version_id, selection):
        document = await self.version("visual_test_spec_versions", project, version_id)
        active = await self.active("visual_test_spec_versions", project, "testcase_id", testcase)
        if document["testcase_id"] != testcase or not active or active["version_id"] != version_id:
            raise HTTPException(409, "Select the current approved test specification.")
        actions, references = await self.validate_specification(project, document)
        environment = await self.db["environments"].find_one({"project_id": project, "env_id": selection.environment_id})
        if not environment:
            raise HTTPException(404, "Environment not found in this project.")
        if environment.get("revision", 0) < 1:
            raise HTTPException(409, "Save the environment to establish its revision first.")
        requires_credentials = any(step.get("value", {}).get("source") == "credential" for step in actions)
        credential = None
        if requires_credentials:
            credential = next((item for item in environment.get("credentials", [])
                               if item.get("role", "").strip().lower() == (selection.application_role or "").lower()), None)
            if not credential or not credential.get("credential_id"):
                raise HTTPException(409, "Credential steps require a saved application role.")
            fields = {step["value"]["field"] for step in actions if step.get("value", {}).get("source") == "credential"}
            if "password" in fields and (not environment.get("secret_payload") or not credential.get("password_configured")):
                raise HTTPException(409, "Password steps require encrypted credentials for the selected role.")
            if "username" in fields and not credential.get("username", "").strip():
                raise HTTPException(409, "The selected role requires a configured username.")
        elif selection.application_role:
            raise HTTPException(422, "This specification uses no credentials. Select no role.")
        manifest = {"schema_version": "1.0", "purpose": "approved-specification-preview", "target_policy": "salesforce-sandbox-preparation-v1", "execution_ready": False,
                    "testcase_id": testcase, "approved_specification_version_id": version_id,
                    "specification_digest": document["content_digest"], "source_digest": document["source_digest"],
                    "workflow_versions": references, "steps": actions, "environment_id": selection.environment_id,
                    "environment_revision": environment["revision"], "environment_digest": digest(environment, self.digest_key),
                    "target_url": sandbox_url(environment.get("base_url")), "application_role": credential["role"] if credential else None,
                    "credential_id": credential["credential_id"] if credential else None,
                    "requires_credentials": requires_credentials}
        manifest.update({key: document[key] for key in ("knowledge_version_id", "knowledge_content_digest", "story_analysis_id") if key in document})
        preview = CompiledSpecificationPreview(**manifest, manifest_digest="0" * 64)
        canonical = preview.model_dump(mode="json", exclude_none=True, exclude={"manifest_digest"})
        return preview.model_copy(update={"manifest_digest": digest(canonical, self.digest_key)})
