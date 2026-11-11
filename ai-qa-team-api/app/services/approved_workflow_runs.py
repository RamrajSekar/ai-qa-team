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
        return {key: value for key, value in document.items() if key != "_id"}

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

    async def cancel(self, project, run_id):
        await self.status(project, run_id)
        await self.db["approved_workflow_runs"].find_one_and_update(
            {"project_id": project, "_id": run_id, "state": "prepared"},
            {"$set": {"state": "cancelled", "verdict": "cancelled", "reason": None,
                      "finished_at": datetime.now(timezone.utc).isoformat()}}, return_document=ReturnDocument.AFTER)
        return await self.status(project, run_id)
