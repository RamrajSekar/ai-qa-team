"""Opt-in synthetic service/Mongo check; no API startup, auth bypass or AI calls.

Uses two random synthetic collections on the development-only configured service.
Never reads or modifies existing application collections.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import certifi
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.write_concern import WriteConcern

from app.config import settings
from app.models.product_knowledge import KnowledgeDraft, KnowledgeSourceInput
from app.services.product_knowledge import ProductKnowledge


async def verify():
    if settings.app_env not in ("development", "local", "test"):
        raise RuntimeError("DEVELOPMENT_CONFIGURATION_REQUIRED")
    name = "qa_knowledge_m1_" + uuid4().hex
    if name == settings.mongo_db or not name.startswith("qa_knowledge_m1_"):
        raise RuntimeError("ISOLATION_CHECK_FAILED")
    client = AsyncIOMotorClient(settings.mongo_uri, tls=True,
        tlsCAFile=settings.mongo_tls_ca_file or certifi.where(),
        serverSelectionTimeoutMS=5000, connectTimeoutMS=5000, socketTimeoutMS=10000)
    development = client.get_database(settings.mongo_db, write_concern=WriteConcern(w="majority", wtimeout=10000))
    allowed = ("product_knowledge_sources", "product_knowledge_versions")
    class IsolatedCollections:
        def __getitem__(self, key):
            if key not in allowed:
                raise RuntimeError("UNEXPECTED_COLLECTION")
            return development[name + "_" + key]
    database = IsolatedCollections()
    old_flag = settings.features.product_knowledge
    created = False
    try:
        await client.admin.command("ping")
        settings.features.product_knowledge = True
        service = ProductKnowledge(database)
        created = True
        source = await service.add_source("synthetic", "synthetic-reviewer", KnowledgeSourceInput(
            title="Synthetic source", kind="document", text="Saving shows Draft saved."))
        claim = {"claim_id": "K1", "category": "business_rule", "statement": "Saving shows Draft saved.",
                 "epistemic_status": "expected", "source_id": source["source_id"], "quote": "Draft saved."}
        first = await service.create_version("synthetic", "synthetic-reviewer", KnowledgeDraft(title="First", claims=[claim]))
        await service.approve("synthetic", "synthetic-reviewer", first["version_id"])
        drafts = [await service.create_version("synthetic", "synthetic-reviewer", KnowledgeDraft(
            title="Incremental", claims=[{**claim, "claim_id": key}])) for key in ("K2", "K3")]
        original = service.active
        readers = 0
        gate = asyncio.Event()

        async def synchronized_read(project):
            nonlocal readers
            snapshot = await original(project)
            readers += 1
            if readers == 2:
                gate.set()
            await gate.wait()
            return snapshot

        service.active = synchronized_read
        results = await asyncio.wait_for(asyncio.gather(*(
            service.approve("synthetic", "synthetic-reviewer", draft["version_id"])
            for draft in drafts), return_exceptions=True), timeout=30)
        service.active = original
        winners = [item for item in results if isinstance(item, dict)]
        conflicts = [item for item in results if isinstance(item, HTTPException) and item.status_code == 409]
        assert len(winners) == 1 and len(conflicts) == 1
        # A fresh service instance recovers approval solely from durable records.
        recovered = ProductKnowledge(database)
        active = await recovered.active("synthetic")
        assert active["version_id"] == winners[0]["version_id"] and len(active["claims"]) == 2
        assert any(item["claim_id"] == "K1" for item in active["claims"])
        await recovered.approve("synthetic", "retry-reviewer", active["version_id"])
        historical = await recovered.record("product_knowledge_versions", "synthetic", first["version_id"])
        assert historical["status"] == "approved" and len(historical["claims"]) == 1
        correction = await recovered.create_version("synthetic", "synthetic-reviewer", KnowledgeDraft(
            title="Correction", parent_version_id=active["version_id"],
            claims=[{**claim, "statement": "Show the reviewed save confirmation."}]))
        corrected = await recovered.approve("synthetic", "synthetic-reviewer", correction["version_id"])
        assert len(corrected["claims"]) == 2 and corrected["changes"][0]["action"] == "replace"
        other_claim = next(item["claim_id"] for item in corrected["claims"] if item["claim_id"] != "K1")
        removal = await recovered.create_version("synthetic", "synthetic-reviewer", KnowledgeDraft(
            title="Explicit removal", parent_version_id=corrected["version_id"], removed_claim_ids=[other_claim]))
        assert len((await recovered.active("synthetic"))["claims"]) == 2
        removed = await recovered.approve("synthetic", "synthetic-reviewer", removal["version_id"])
        assert len(removed["claims"]) == 1
        assert await recovered.active("another-project") is None
        return {"real_mongo": True, "competing_approvals": 2, "winners": 1, "conflicts": 1,
                "incremental_preservation": True, "restart_read": True, "history": True,
                "targeted_correction": True, "explicit_removal": True, "project_isolation": True, "ai_calls": 0}
    finally:
        settings.features.product_knowledge = old_flag
        try:
            if created:
                # Only these generated throwaway collection names can be deleted.
                for key in allowed:
                    target = name + "_" + key
                    if not target.startswith("qa_knowledge_m1_"):
                        raise RuntimeError("ISOLATION_CHECK_FAILED")
                    await development.drop_collection(target)
        finally:
            client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--configured-service-is-development", action="store_true", required=True)
    parser.parse_args()
    try:
        result = asyncio.run(verify())
        print(json.dumps({**result, "temporary_collections_deleted": True}))
    except Exception as error:
        # No raw provider/database errors, hostnames, paths or credentials.
        print(json.dumps({"result": "NOT_VERIFIED", "error_type": type(error).__name__, "mongo_error_code": getattr(error, "code", None)}))
        sys.exit(1)
