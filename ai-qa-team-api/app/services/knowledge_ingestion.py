"""Disabled-by-default development intake. No parsing or model calls in API requests."""
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import Field
from app.config import settings
from app.models.approved_visual_run import Contract, VisibleText, Digest
from app.utils.feature_flags import require_features


class UploadAdmission(Contract):
    title: VisibleText
    format: Literal["txt", "pdf", "docx"]
    size_bytes: int = Field(ge=1, le=104857600)
    sha256: Digest
    consent_ai: bool = False
    interpret_images: bool = False


class DecodedPage(Contract):
    page: int | None = Field(default=None,ge=1,le=50)
    block: int | None = Field(default=None,ge=1,le=500)
    text: str = Field(max_length=60000)


class DecodedImage(Contract):
    image_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    page: int | None = Field(default=None,ge=1,le=50)


class DecodedOutput(Contract):
    pages: list[DecodedPage] = Field(max_length=500)
    images: list[DecodedImage] = Field(max_length=4)


class PrivateDevelopmentStore:
    """Not a production bucket adapter. Object keys are entirely server-owned."""
    def __init__(self):
        config = settings.knowledge_ingestion
        if (config.storage_backend != "local_dev" or not config.allow_local_development
                or settings.app_env.lower() not in {"development", "local", "test"}
                or not config.local_private_root):
            raise HTTPException(503, "Private ingestion storage is not configured and qualified.")
        root = Path(config.local_private_root)
        if not root.is_absolute() or root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
            raise HTTPException(503, "Private ingestion storage configuration is invalid.")
        self.root = root.resolve()
        if any(part.lower() in {"public", "static", ".next"} for part in self.root.parts):
            raise HTTPException(503, "Ingestion storage must not be web-served.")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def folder(self, project, identity):
        if not re.fullmatch(r"[0-9a-f]{32}", identity): raise HTTPException(404, "Upload not found.")
        directory = self.root / hashlib.sha256(project.encode()).hexdigest() / identity
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.resolve() != directory or any(p.is_symlink() for p in (directory, directory.parent)):
            raise HTTPException(503, "Private ingestion workspace is invalid.")
        return directory

    def delete(self, project, identity):
        # Only fixed filenames or generated UUID PNGs, never recursive arbitrary paths.
        folder = self.folder(project, identity)
        for path in folder.iterdir():
            if path.is_file() and not path.is_symlink() and (path.name in {"input", "cancel", "result.json"} or re.fullmatch(r"[0-9a-f]{32}\.png", path.name)):
                path.unlink()


class KnowledgeIngestion:
    def __init__(self, database): self.db = database

    @staticmethod
    def guard():
        require_features("product_knowledge", "knowledge_uploads")
        if not settings.knowledge_ingestion.infrastructure_verified:
            raise HTTPException(503, "Private storage, processing limits, retention and deletion must be qualified before uploads are enabled.")
        if not settings.knowledge_ingestion.decoder_engine or not settings.knowledge_ingestion.decoder_image:
            raise HTTPException(503, "Restricted document decoder is not configured.")
        return PrivateDevelopmentStore()

    @staticmethod
    def public(row):
        return {key: row.get(key) for key in ("upload_id", "title", "format", "state", "error_code", "created_at", "expires_at", "source_ids", "images")}

    async def row(self, project, identity):
        row = await self.db["knowledge_ingestion_jobs"].find_one({"project_id": project, "upload_id": identity})
        if not row: raise HTTPException(404, "Upload not found in this project.")
        return row

    async def admit(self, project, actor, payload):
        self.guard()
        if payload.size_bytes > settings.knowledge_ingestion.max_upload_bytes: raise HTTPException(413, "Upload exceeds the configured size limit.")
        if payload.interpret_images:
            require_features("knowledge_image_interpretation")
            if not payload.consent_ai: raise HTTPException(422, "Image interpretation needs explicit AI consent.")
            if payload.format == "docx": raise HTTPException(422, "Export DOCX as PDF for image interpretation with page references.")
        identity = uuid4().hex; now = datetime.now(timezone.utc)
        row = {**payload.model_dump(), "_id": identity, "upload_id": identity, "project_id": project,
            "requested_by": actor, "state": "awaiting_upload", "created_at": now.isoformat(),
            "delete_requested": False,
            "expires_at": (now + timedelta(days=settings.knowledge_ingestion.retention_days)).isoformat(), "source_ids": [], "images": []}
        await self.db["knowledge_ingestion_jobs"].insert_one(row)
        return self.public(row)

    async def receive(self, project, identity, chunks):
        store = self.guard(); row = await self.row(project, identity)
        if row["state"] != "awaiting_upload": raise HTTPException(409, "This upload is already submitted; do not replay it.")
        path = store.folder(project, identity) / "input"
        try:
            with path.open("xb") as stream:
                count = 0; checksum = hashlib.sha256()
                async for chunk in chunks:
                    count += len(chunk)
                    if count > min(row["size_bytes"], settings.knowledge_ingestion.max_upload_bytes): raise HTTPException(413, "Upload exceeds its admitted size.")
                    checksum.update(chunk); stream.write(chunk)
            if count != row["size_bytes"] or checksum.hexdigest() != row["sha256"]: raise HTTPException(422, "Upload size or checksum did not match.")
            result = await self.db["knowledge_ingestion_jobs"].update_one({"project_id": project, "upload_id": identity, "state": "awaiting_upload", "delete_requested": False}, {"$set": {"state": "queued"}})
            if not result.matched_count: raise HTTPException(409, "Upload was cancelled while receiving content.")
        except FileExistsError:
            raise HTTPException(409, "Upload content already exists. Inspect status or delete it before creating another upload.") from None
        except BaseException:
            path.unlink(missing_ok=True)
            await self.db["knowledge_ingestion_jobs"].update_one({"project_id": project, "upload_id": identity, "state": "awaiting_upload"}, {"$set": {"state": "failed", "error_code": "UPLOAD_REJECTED"}})
            raise
        return self.public(await self.row(project, identity))

    async def delete(self, project, identity):
        store = PrivateDevelopmentStore(); row = await self.row(project, identity)
        await self.db["knowledge_ingestion_jobs"].update_one({"project_id": project, "upload_id": identity}, {"$set": {"delete_requested": True}})
        (store.folder(project, identity) / "cancel").touch()
        row = await self.row(project, identity)
        if row["state"] == "processing":
            return {"state": "cancelling"}
        store.delete(project, identity)
        await self.db["knowledge_ingestion_jobs"].update_one({"project_id": project, "upload_id": identity}, {"$set": {"state": "deleted", "images": []}})
        return {"state": "deleted"}

    async def reconcile_and_expire(self, now):
        """Operator cleanup works even after intake is disabled; never requeue work."""
        PrivateDevelopmentStore()
        await self.db["knowledge_ingestion_jobs"].update_many({"state":"processing","lease_expires_at":{"$lt":now.isoformat()}},
            {"$set":{"state":"blocked","error_code":"INTERRUPTED_NO_REPLAY"}})
        rows=await self.db["knowledge_ingestion_jobs"].find({"expires_at":{"$lt":now.isoformat()},
            "state":{"$in":["ready","failed","blocked","queued","awaiting_upload"]}}).limit(100).to_list(100)
        for row in rows: await self.delete(row["project_id"],row["upload_id"])
        return len(rows)
