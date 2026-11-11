"""Durable staging preparation only. No browser, secret resolution or dispatch."""
from datetime import datetime, timezone
import hmac
import json
from urllib.parse import urlsplit

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.models.approved_visual_run import (
    PreparedStagingBinding, StagingBindingPreview, StagingBindingSelection,
    StagingBindingState, VisualRunSelection,
)
from app.services.approved_visual_run import digest


def sandbox_url(value):
    if not isinstance(value, str) or not value or any(ord(char) <= 32 for char in value) or "\\" in value:
        raise HTTPException(422, "A Salesforce Sandbox login URL is required.")
    candidate = value if "://" in value else "https://" + value
    try:
        parsed = urlsplit(candidate)
        valid = (parsed.scheme == "https" and parsed.hostname == "test.salesforce.com"
                 and parsed.port in (None, 443) and not parsed.username and not parsed.password
                 and not parsed.query and not parsed.fragment and parsed.path in ("", "/", "/login"))
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(422, "Use the approved HTTPS Salesforce Sandbox login URL without embedded credentials, query parameters or fragments.")
    return "https://test.salesforce.com" + (parsed.path or "/")


class StagingRunBindings:
    def __init__(self, approvals):
        self.approvals = approvals
        self.db = approvals.db

    async def preview(self, project_id, selection):
        approved = await self.approvals.preview(project_id, VisualRunSelection(
            approved_test_version_id=selection.approved_test_version_id,
            environment_id=selection.environment_id,
        ))
        environment = await self.db["environments"].find_one({
            "project_id": project_id, "env_id": selection.environment_id,
        })
        if not environment or digest(environment, self.approvals.environment_digest_key) != approved.environment_digest:
            raise HTTPException(409, "Environment changed. Preview again.")
        revision = environment.get("revision", 0)
        credential = next((item for item in environment.get("credentials", [])
                           if item.get("role", "").strip().lower() == selection.application_role.lower()), None)
        if not credential:
            raise HTTPException(422, "Select an application role saved in this environment.")
        if (not isinstance(revision, int) or revision < 1 or not environment.get("secret_payload")
                or not credential.get("credential_id") or not credential.get("password_configured")
                or not credential.get("username", "").strip()):
            raise HTTPException(409, "Save this environment with encrypted credentials before preparing a login binding.")
        fields = {
            "project_id": project_id, "testcase_id": approved.test.testcase_id,
            "approved_test_version_id": approved.test.version_id,
            "approved_test_content_digest": approved.test.content_digest,
            "source_digest": approved.test.source_digest,
            "environment_id": selection.environment_id, "environment_revision": revision,
            "environment_digest": approved.environment_digest,
            "target_url": sandbox_url(environment.get("base_url")),
            "application_role": credential["role"].strip(), "credential_id": credential["credential_id"],
            "purpose": "staging-login-preparation", "target_policy": "salesforce-sandbox-preparation-v1",
            "execution_ready": False,
        }
        return StagingBindingPreview(**fields, binding_digest=digest(fields, self.approvals.environment_digest_key))

    async def save(self, project_id, requester, payload):
        collection = self.db["approved_staging_bindings"]
        binding_id = digest(["staging-binding-v1", project_id, requester, payload.idempotency_key])
        query = {"_id": binding_id, "project_id": project_id}
        request_digest = digest(payload.model_dump())
        existing = await collection.find_one(query)
        if existing:
            return self.replay(existing, request_digest)
        preview = await self.preview(project_id, payload)
        if not hmac.compare_digest(preview.binding_digest, payload.binding_digest):
            raise HTTPException(409, "Binding inputs changed. Preview again.")
        binding = PreparedStagingBinding(**preview.model_dump(), binding_id=binding_id,
                                         prepared_by=requester, prepared_at=datetime.now(timezone.utc))
        try:
            await collection.insert_one({**query, "request_digest": request_digest,
                                         "testcase_id": binding.testcase_id, "prepared_at": binding.prepared_at,
                                         "binding": binding.model_dump(mode="json")})
        except DuplicateKeyError:
            existing = await collection.find_one(query)
            if not existing:
                raise
            return self.replay(existing, request_digest)
        return binding

    async def status(self, project_id, binding_id):
        document = await self.db["approved_staging_bindings"].find_one({"project_id": project_id, "_id": binding_id})
        if not document:
            raise HTTPException(404, "Staging binding not found.")
        return await self.validate(project_id, self.read(document))

    async def latest(self, project_id, testcase_id):
        document = await self.db["approved_staging_bindings"].find_one(
            {"project_id": project_id, "testcase_id": testcase_id}, sort=[("prepared_at", -1), ("_id", -1)],
        )
        return await self.validate(project_id, self.read(document)) if document else None

    async def validate(self, project_id, binding):
        try:
            current = await self.preview(project_id, StagingBindingSelection(
                approved_test_version_id=binding.approved_test_version_id, environment_id=binding.environment_id,
                application_role=binding.application_role,
            ))
            if hmac.compare_digest(current.binding_digest, binding.binding_digest):
                return StagingBindingState(binding=binding, validation_state="current")
        except HTTPException as exc:
            if exc.status_code not in (404, 409, 422):
                raise
        return StagingBindingState(binding=binding, validation_state="stale",
                                   reason="Bound inputs changed or are no longer available. Preview and prepare a new binding.")

    @staticmethod
    def read(document):
        return PreparedStagingBinding.model_validate_json(json.dumps(document["binding"]))

    @classmethod
    def replay(cls, document, request_digest):
        if document["request_digest"] != request_digest:
            raise HTTPException(409, "Idempotency key was used with different binding inputs.")
        return cls.read(document)
