"""Opt-in real development Mongo checks, optional actual BrowserStack readiness.

Uses isolated prefixed collections and synthetic authorization, not real UI/login.
No normal projects/accounts are read or modified. Evidence contains no provider handles.
"""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch, AsyncMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings, FeatureFlags
from app.db.connection import client, db
from app.models.visual_specification import SpecificationDraft, SpecificationPreviewSelection, SpecificationRunAdmission, WorkflowDraft
from app.services.approved_workflow_runs import ApprovedWorkflowRuns
from app.services.visual_specifications import VisualSpecifications
from app.workers.approved_workflow_worker import WorkflowWorker, IsolatedPreflight
from app.workers import approved_workflow_worker as worker_module


class FixtureDatabase:
    def __init__(self, prefix): self.prefix, self.names, self.shared_slot = prefix, set(), False
    def __getitem__(self, name):
        if name == "approved_visual_execution_slots" and self.shared_slot:
            return db[name]
        self.names.add(self.prefix + name)
        return db[self.prefix + name]


class SyntheticTransport:
    def __init__(self, entered=None, release=None): self.entered, self.release = entered, release
    async def run(self, document, checkpoint, event):
        await checkpoint()
        if self.entered: self.entered.set()
        if self.release: await self.release.wait()
        await checkpoint()
        return True
    async def close(self): return True


async def fixture_authorization(database, document):
    # This is a synthetic account/project fixture, not a normal logged-in account.
    if document["project_id"] != "WORKER_FIXTURE" or document["dispatch_requested_by"] != "fixture-reviewer":
        raise RuntimeError("Fixture access rejected")


async def main(remote, cancel_remote=False):
    if settings.app_env not in ("development", "dev", "local", "test"):
        raise RuntimeError("Development configuration required")
    prefix = "workflow_verify_" + uuid4().hex + "_"
    fixture = FixtureDatabase(prefix)
    evidence = {"environment": "real development Mongo; synthetic authorization",
                "remote_browser": "NOT RUN", "checks": {}}
    settings.features = FeatureFlags(reusable_workflows=True, approved_visual_run_admission=True, approved_workflow_worker=True)
    project = "WORKER_FIXTURE"
    key = settings.jwt_secret_key.encode()
    service = ApprovedWorkflowRuns(fixture, key)
    specs = VisualSpecifications(fixture, key)
    remote_run_id = None
    # No real credentials or URL navigation: the selected environment only exercises pinning.
    try:
        await asyncio.wait_for(client.admin.command("ping"), 10)
        await fixture["testcases"].insert_one({"_id": "case", "project_id": project, "testcase_id": "TC_FIXTURE", "scenario_id": "SC_FIXTURE"})
        await fixture["scenarios"].insert_one({"_id": "scenario", "project_id": project, "scenario_id": "SC_FIXTURE", "story_id": "ST_FIXTURE", "approved": True})
        await fixture["stories"].insert_one({"_id": "story", "project_id": project, "story_id": "ST_FIXTURE", "acceptance_criteria": "Show synthetic confirmation."})
        await fixture["environments"].insert_one({"_id": "env", "project_id": project, "env_id": "ENV_FIXTURE", "revision": 1,
                                                "base_url": "https://test.salesforce.com", "credentials": []})
        workflow = await specs.create_workflow(project, "fixture-reviewer", WorkflowDraft(title="Synthetic reusable check",
            steps=[{"action": "assert_text", "expected": "Synthetic confirmation"}]))
        await specs.approve_workflow(project, "fixture-reviewer", workflow["version_id"])
        version = await specs.create_specification(project, "TC_FIXTURE", "fixture-reviewer", SpecificationDraft(steps=[{"action": "reusable", "workflow_version_id": workflow["version_id"]}]))
        await specs.approve_specification(project, "TC_FIXTURE", "fixture-reviewer", version["version_id"])
        preview = await specs.preview(project, "TC_FIXTURE", version["version_id"], SpecificationPreviewSelection(environment_id="ENV_FIXTURE"))

        async def admission(identity=None):
            payload = SpecificationRunAdmission(environment_id="ENV_FIXTURE", preview_digest=preview.manifest_digest, idempotency_key=identity or uuid4().hex)
            return await service.admit(project, "TC_FIXTURE", version["version_id"], "fixture-reviewer", payload)

        identity = uuid4().hex
        first, duplicate = await asyncio.gather(admission(identity), admission(identity))
        assert first["run_id"] == duplicate["run_id"]
        assert await fixture["approved_workflow_runs"].count_documents({}) == 1
        original = first["manifest"]
        assert original["workflow_versions"][0]["version_id"] == workflow["version_id"]
        evidence["checks"]["concurrent_idempotent_admission"] = "PASS"
        restored = await ApprovedWorkflowRuns(fixture, key).status(project, first["run_id"])
        assert restored["manifest"] == original
        # Fresh OS process reads the record using the same dev settings, not an in-memory object.
        code = '''import asyncio,json,sys
from app.db.connection import db
async def read():
    d=await db[sys.argv[1]].find_one({"_id":sys.argv[2]})
    print(json.dumps({"run_id":d["run_id"],"manifest_digest":d["manifest_digest"]}))
asyncio.run(read())
'''
        child = await asyncio.create_subprocess_exec(sys.executable, "-c", code, prefix + "approved_workflow_runs", first["run_id"],
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        try:
            output, _ = await asyncio.wait_for(child.communicate(), 20)
        finally:
            if child.returncode is None:
                child.kill(); await child.wait()
        assert child.returncode == 0 and json.loads(output)["manifest_digest"] == first["manifest_digest"]
        evidence["checks"]["fresh_process_persistence_read"] = "PASS"

        second = await admission()
        await service.queue_preflight(project, first["run_id"], "fixture-reviewer")
        await service.queue_preflight(project, second["run_id"], "fixture-reviewer")
        entered, release = asyncio.Event(), asyncio.Event()
        one = WorkflowWorker(fixture, key, lambda: SyntheticTransport(entered, release), fixture_authorization)
        two = WorkflowWorker(fixture, key, SyntheticTransport, fixture_authorization)
        # Synthetic transport credentials avoid dependence on provider config for lease tests.
        saved = settings.browserstack_username, settings.browserstack_access_key
        settings.browserstack_username, settings.browserstack_access_key = "fixture", "fixture"
        task = asyncio.create_task(one.once())
        await asyncio.wait_for(entered.wait(), 15)
        assert not await two.once()
        evidence["checks"]["actual_mongo_slot_contention"] = "PASS"
        await service.cancel(project, first["run_id"])
        release.set(); await asyncio.wait_for(task, 15)
        assert (await service.status(project, first["run_id"]))["state"] == "cancelled"
        assert await two.once()
        assert (await service.status(project, second["run_id"]))["browser_readiness"] == "ready"
        assert await fixture["approved_visual_execution_slots"].count_documents({}) == 0
        evidence["checks"]["cancel_cleanup_and_subsequent_admission"] = "PASS (synthetic transport)"
        assert (await service.status(project, first["run_id"]))["manifest"] == original
        settings.browserstack_username, settings.browserstack_access_key = saved

        interrupted = await admission()
        await service.queue_preflight(project, interrupted["run_id"], "fixture-reviewer")
        expired = datetime.now(timezone.utc) - timedelta(seconds=1)
        await fixture["approved_workflow_runs"].update_one({"_id": interrupted["run_id"]}, {"$set": {
            "state": "running", "execution_token": "fixture-token", "lease_expires_at": expired, "remote_session_id": "fixture-only-session"}})
        await fixture["approved_visual_execution_slots"].insert_one({"_id": worker_module.SLOT, "run_id": interrupted["run_id"],
            "token": "fixture-token", "expires_at": datetime(9999, 1, 1, tzinfo=timezone.utc)})
        with patch.object(worker_module, "close_remote", AsyncMock(return_value=True)):
            await WorkflowWorker(fixture, key, authorizer=fixture_authorization).reconcile()
        recovered = await service.status(project, interrupted["run_id"])
        assert recovered["state"] == "completed" and recovered["reason"] == "WORKER_INTERRUPTED"
        assert await fixture["approved_visual_execution_slots"].count_documents({}) == 0
        assert (await service.status(project, second["run_id"]))["browser_readiness"] == "ready"
        evidence["checks"]["interrupted_lease_recovery_without_replay"] = "PASS (simulated interruption/cleanup)"

        stale = await admission()
        queued_stale = await admission()
        await service.queue_preflight(project, queued_stale["run_id"], "fixture-reviewer")
        await fixture["environments"].update_one({"_id": "env"}, {"$set": {"revision": 2}})
        try:
            await service.queue_preflight(project, stale["run_id"], "fixture-reviewer")
            raise AssertionError("Stale environment admitted")
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 409
        await WorkflowWorker(fixture, key, SyntheticTransport, fixture_authorization).once()
        assert (await service.status(project, queued_stale["run_id"]))["reason"] == "DISPATCH_INPUTS_OR_ACCESS_CHANGED"
        assert await fixture["approved_visual_execution_slots"].count_documents({}) == 0
        evidence["checks"]["stale_inputs_rechecked_at_worker_claim"] = "PASS"
        await fixture["environments"].update_one({"_id": "env"}, {"$set": {"revision": 1}})
        evidence["checks"]["stale_environment_rejected"] = "PASS"

        stale_workflow = await admission()
        successor = await specs.create_workflow(project, "fixture-reviewer", WorkflowDraft(workflow_id=workflow["workflow_id"],
            title="Reviewed successor", steps=[{"action": "assert_text", "expected": "Synthetic confirmation"}]))
        await specs.approve_workflow(project, "fixture-reviewer", successor["version_id"])
        try:
            await service.queue_preflight(project, stale_workflow["run_id"], "fixture-reviewer")
            raise AssertionError("Stale reusable workflow admitted")
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 409
        evidence["checks"]["stale_workflow_version_rejected"] = "PASS"
        assert (await service.status(project, first["run_id"]))["manifest"] == original
        version = await specs.create_specification(project, "TC_FIXTURE", "fixture-reviewer", SpecificationDraft(steps=[{"action": "reusable", "workflow_version_id": successor["version_id"]}]))
        await specs.approve_specification(project, "TC_FIXTURE", "fixture-reviewer", version["version_id"])
        preview = await specs.preview(project, "TC_FIXTURE", version["version_id"], SpecificationPreviewSelection(environment_id="ENV_FIXTURE"))

        if remote:
            if not all(saved): raise RuntimeError("BrowserStack configuration unavailable")
            settings.visual_runner_python = str(Path(__file__).resolve().parents[2] / "visual-runner" / ".venv" / "Scripts" / "python.exe") if sys.platform == "win32" else str(Path(__file__).resolve().parents[2] / "visual-runner" / ".venv" / "bin" / "python")
            run = await admission()
            remote_run_id = run["run_id"]
            fixture.shared_slot = True
            await service.queue_preflight(project, run["run_id"], "fixture-reviewer")
            cancellation_sent = False
            class CancelAfterSession(IsolatedPreflight):
                async def run(self, document, checkpoint, session_event):
                    async def event(identity):
                        nonlocal cancellation_sent
                        await session_event(identity)
                        await service.cancel(project, document["run_id"])
                        cancellation_sent = True
                    return await super().run(document, checkpoint, event)
            transport = CancelAfterSession() if cancel_remote else IsolatedPreflight()
            worker = WorkflowWorker(fixture, key, transport_factory=lambda: transport, authorizer=fixture_authorization)
            started = time.monotonic()
            task = asyncio.create_task(worker.once())
            claimed = await asyncio.wait_for(task, 110)
            result = await service.status(project, run["run_id"])
            evidence["remote_browser"] = {name: result.get(name) for name in ("state", "verdict", "reason", "browser_readiness", "cleanup_confirmed")}
            evidence["remote_browser"].update({"claimed": claimed, "elapsed_ms": round((time.monotonic()-started)*1000),
                "separate_runner_process": bool(transport.process and transport.process.pid != os.getpid()),
                "runner_exited": bool(transport.process and transport.process.returncode is not None)})
            if cancel_remote:
                evidence["remote_browser"]["cancellation_sent_after_session_event"] = cancellation_sent
            print(json.dumps(evidence, indent=2))
            assert result.get("cleanup_confirmed")
            if cancel_remote:
                assert cancellation_sent and result["state"] == "cancelled"
            else:
                assert result.get("browser_readiness") == "ready"
        else:
            print(json.dumps(evidence, indent=2))
    finally:
        retained = remote_run_id and await db["approved_visual_execution_slots"].find_one({"run_id": remote_run_id})
        if retained:
            print(json.dumps({"fixture_records_retained_for_cleanup": prefix, "cleanup_confirmed": False}))
        # Delete only the exact random-prefix collections created by this harness.
        for name in (() if retained else fixture.names):
            if not name.startswith(prefix): raise RuntimeError("Fixture namespace mismatch")
            await db.drop_collection(name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--browserstack", action="store_true")
    parser.add_argument("--cancel-browserstack", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.browserstack or args.cancel_browserstack, args.cancel_browserstack))
    except Exception as exc:
        raise SystemExit("Development worker verification failed: " + type(exc).__name__) from None
