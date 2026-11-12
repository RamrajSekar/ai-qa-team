"""Immutable compiled run admissions. No implicit launch or legacy queue writes."""
from datetime import datetime, timezone
import hmac

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.models.visual_specification import SpecificationPreviewSelection
from app.services.approved_visual_run import digest
from app.services.visual_specifications import VisualSpecifications
from app.utils.feature_flags import require_features


class ApprovedWorkflowRuns:
    def __init__(self, database, key):
        self.db = database
        self.key = key
        self.specifications = VisualSpecifications(database, key)

    @staticmethod
    def public(document):
        # Private execution fencing/session handles must never enter API responses.
        keys = ("run_id", "project_id", "manifest", "manifest_digest", "state", "verdict", "execution_ready",
                "reason", "created_at", "queued_at", "started_at", "finished_at", "browser_readiness", "cleanup_confirmed")
        return {key: document[key] for key in keys if key in document}

    async def validate_current(self, document):
        require_features("reusable_workflows", "approved_visual_run_admission")
        manifest = document["manifest"]
        if not hmac.compare_digest(document["manifest_digest"], digest(manifest, self.key)):
            raise HTTPException(409, "Run manifest integrity check failed.")
        if (manifest.get("project_id") != document["project_id"] or manifest.get("execution_adapter") != "browserstack-direct-webdriver-v1"
                or manifest.get("purpose") != "approved-workflow-run-v1" or manifest.get("runtime_contract") != "robot-visual-workflow-v1"):
            raise HTTPException(409, "Unsupported run identity.")
        # Turning knowledge mode off must not bypass the approval pins of a saved run.
        from app.config import settings
        if manifest.get("knowledge_version_id") and not settings.features.product_knowledge:
            raise HTTPException(409, "This run requires its knowledge review policy to remain enabled.")
        current = await self.specifications.preview(document["project_id"], manifest["testcase_id"],
            manifest["approved_specification_version_id"], SpecificationPreviewSelection(
                environment_id=manifest["environment_id"], application_role=manifest.get("application_role")))
        if not hmac.compare_digest(current.manifest_digest, manifest["preview_digest"]):
            raise HTTPException(409, "Approved run inputs changed. Prepare a new admission.")

    async def queue_preflight(self, project, run_id, actor):
        require_features("approved_workflow_worker")
        from app.config import settings
        if settings.app_env not in ("development", "dev", "test", "local"):
            raise HTTPException(403, "Workflow worker is development-only.")
        await self.status(project, run_id)
        document = await self.db["approved_workflow_runs"].find_one({"project_id": project, "_id": run_id})
        await self.validate_current(document)
        if document["state"] != "prepared":
            return self.public(document)  # Never replay a completed/interrupted preparation.
        await self.db["approved_workflow_runs"].find_one_and_update(
            {"project_id": project, "_id": run_id, "state": "prepared"},
            {"$set": {"state": "queued", "reason": "BROWSER_PREFLIGHT_QUEUED", "dispatch_requested_by": actor,
                      "queued_at": datetime.now(timezone.utc).isoformat(), "operation": "browser-readiness-v1"}},
            return_document=ReturnDocument.AFTER)
        return await self.status(project, run_id)

    async def admit(self, project, testcase, version, actor, payload):
        require_features("reusable_workflows", "approved_visual_run_admission")
        identity = digest(["approved-workflow-run-v1", project, actor, payload.idempotency_key])
        query = {"_id": identity, "project_id": project}
        request_digest = digest([testcase, version, payload.model_dump()])
        existing = await self.db["approved_workflow_runs"].find_one(query)
        if existing:
            return self.match(existing, request_digest)
        preview = await self.specifications.preview(project, testcase, version, SpecificationPreviewSelection(
            environment_id=payload.environment_id, application_role=payload.application_role))
        if not hmac.compare_digest(payload.preview_digest, preview.manifest_digest):
            raise HTTPException(409, "Run inputs changed. Preview and review the current selection again.")
        manifest = preview.model_dump(mode="json", exclude_none=True)
        manifest["preview_digest"] = manifest.pop("manifest_digest")
        manifest.update({"purpose": "approved-workflow-run-v1", "project_id": project,
                         "execution_adapter": "browserstack-direct-webdriver-v1",
                         "requested_by": actor, "runtime_contract": "robot-visual-workflow-v1"})
        # Neither credentials nor the complete environment are included in this snapshot.
        document = {**query, "run_id": identity, "request_digest": request_digest,
                    "manifest": manifest, "manifest_digest": digest(manifest, self.key),
                    "state": "prepared", "verdict": None, "execution_ready": False,
                    "reason": "GENERAL_WORKER_NOT_ENABLED", "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            await self.db["approved_workflow_runs"].insert_one(document)
        except DuplicateKeyError:
            return self.match(await self.db["approved_workflow_runs"].find_one(query), request_digest)
        return self.public(document)

    def match(self, document, request_digest):
        if not document or document["request_digest"] != request_digest:
            raise HTTPException(409, "The admission key was already used for different inputs.")
        return self.public(document)

    async def status(self, project, run_id):
        require_features("reusable_workflows", "approved_visual_run_admission")
        document = await self.db["approved_workflow_runs"].find_one({"project_id": project, "_id": run_id})
        if not document:
            raise HTTPException(404, "Run admission not found in this project.")
        return self.public(document)

    async def latest(self, project, testcase):
        require_features("reusable_workflows", "approved_visual_run_admission")
        document = await self.db["approved_workflow_runs"].find_one(
            {"project_id": project, "manifest.testcase_id": testcase}, sort=[("created_at", -1), ("_id", -1)])
        return self.public(document) if document else None

    async def cancel(self, project, run_id):
        current = await self.status(project, run_id)
        state = current["state"]
        if state not in ("prepared", "queued", "running", "cancelling"):
            return current
        terminal = state in ("prepared", "queued")
        await self.db["approved_workflow_runs"].find_one_and_update(
            {"project_id": project, "_id": run_id, "state": state},
            {"$set": {"state": "cancelled" if terminal else "cancelling", "verdict": "cancelled" if terminal else None,
                      "reason": None, **({"finished_at": datetime.now(timezone.utc).isoformat()} if terminal else {})}},
            return_document=ReturnDocument.AFTER)
        return await self.status(project, run_id)
