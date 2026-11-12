"""Worker lifecycle/leases with auth, transport and Mongo doubles; no real provider."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
import sys
import json

import httpx

from fastapi import HTTPException

with patch.dict(os.environ, {"MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "worker_tests", "REDIS_HOST": "localhost",
                            "REDIS_PORT": "6399", "REDIS_USERNAME": "", "REDIS_PASSWORD": "", "SESSION_SECRET_KEY": "test", "JWT_SECRET_KEY": "test"}):
    from app.config import settings, FeatureFlags
    from app.workers import approved_workflow_worker as module
    from app.services.approved_workflow_runs import ApprovedWorkflowRuns
    from test_visual_specifications import Collection


class Transport:
    def __init__(self, *, ready=True, cleanup=True, hold=None, entered=None, error=None):
        self.ready, self.cleanup, self.hold, self.entered, self.error = ready, cleanup, hold, entered, error
        self.closed = False

    async def run(self, document, checkpoint, event):
        await checkpoint()
        await event("private-session-canary")
        if self.entered: self.entered.set()
        if self.hold: await self.hold.wait()
        await checkpoint()
        if self.error: raise self.error
        return self.ready

    async def close(self):
        self.closed = True
        return self.cleanup


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.document = {"_id": "a" * 64, "run_id": "a" * 64, "project_id": "P1", "state": "queued", "queued_at": "2026-11-11",
            "operation": "browser-readiness-v1", "dispatch_requested_by": "member", "manifest": {"immutable": "canary"}, "manifest_digest": "b" * 64}
        self.db = {"approved_workflow_runs": Collection(deepcopy(self.document)), "approved_visual_execution_slots": Collection()}
        self.auth = AsyncMock()
        for key, value in (("features", FeatureFlags(reusable_workflows=True, approved_visual_run_admission=True, approved_workflow_worker=True)),
                           ("app_env", "test"), ("browserstack_username", "synthetic"), ("browserstack_access_key", "synthetic")):
            patcher = patch.object(settings, key, value); patcher.start(); self.addCleanup(patcher.stop)

    def worker(self, transport):
        worker = module.WorkflowWorker(self.db, b"test", transport_factory=lambda: transport, authorizer=self.auth)
        worker.service.validate_current = AsyncMock()
        return worker

    async def test_readiness_never_passes_case_and_hides_private_fields(self):
        transport = Transport()
        worker = self.worker(transport)
        self.assertTrue(await worker.once())
        result = self.db["approved_workflow_runs"].docs[0]
        self.assertEqual((result["state"], result["verdict"], result["reason"]), ("completed", "blocked", "ACTION_RUNTIME_NOT_ENABLED"))
        self.assertEqual(result["browser_readiness"], "ready")
        self.assertEqual(result["manifest"], self.document["manifest"])
        self.assertTrue(transport.closed)
        public = ApprovedWorkflowRuns.public(result)
        for key in ("remote_session_id", "execution_token", "lease_expires_at", "dispatch_requested_by"):
            self.assertNotIn(key, public)
        self.assertEqual(self.db["approved_visual_execution_slots"].docs, [])
        self.assertFalse(await worker.once())

    async def test_concurrent_claim_and_cancellation_only_launch_one(self):
        hold, entered = asyncio.Event(), asyncio.Event()
        first = self.worker(Transport(hold=hold, entered=entered))
        second_transport = Transport()
        second = self.worker(second_transport)
        task = asyncio.create_task(first.once())
        await asyncio.wait_for(entered.wait(), 2)
        self.assertFalse(await second.once())
        await first.service.cancel("P1", self.document["run_id"])
        hold.set(); await task
        result = self.db["approved_workflow_runs"].docs[0]
        self.assertEqual(result["state"], "cancelled")
        self.assertFalse(second_transport.closed)
        self.assertEqual(self.db["approved_visual_execution_slots"].docs, [])

    async def test_stale_input_and_revoked_access_block_before_transport(self):
        transport = Transport(); worker = self.worker(transport)
        worker.service.validate_current.side_effect = HTTPException(409)
        await worker.once()
        self.assertFalse(transport.closed)
        self.assertEqual(self.db["approved_workflow_runs"].docs[0]["reason"], "DISPATCH_INPUTS_OR_ACCESS_CHANGED")
        self.db["approved_workflow_runs"].docs = [deepcopy(self.document)]
        worker.service.validate_current.side_effect = None
        self.auth.side_effect = HTTPException(404)
        await worker.once()
        self.assertFalse(transport.closed)
        self.assertEqual(self.db["approved_visual_execution_slots"].docs, [])

    async def test_disabling_knowledge_cannot_bypass_a_pinned_manifest(self):
        from app.services.approved_visual_run import digest
        manifest = {"project_id": "P1", "execution_adapter": "browserstack-direct-webdriver-v1",
                    "purpose": "approved-workflow-run-v1", "runtime_contract": "robot-visual-workflow-v1",
                    "knowledge_version_id": "e" * 32}
        document = {"project_id": "P1", "manifest": manifest, "manifest_digest": digest(manifest, b"test")}
        with self.assertRaises(HTTPException) as failure:
            await ApprovedWorkflowRuns(self.db, b"test").validate_current(document)
        self.assertEqual(failure.exception.status_code, 409)
        self.assertIn("knowledge", failure.exception.detail)

    async def test_unconfirmed_cleanup_holds_slot_and_needs_review(self):
        transport = Transport(cleanup=False, error=RuntimeError("DO_NOT_EXPOSE_CANARY"))
        worker = self.worker(transport); await worker.once()
        result = self.db["approved_workflow_runs"].docs[0]
        self.assertEqual(result["verdict"], "needs_review")
        self.assertEqual(result["reason"], "REMOTE_CLEANUP_UNCONFIRMED")
        self.assertNotIn("DO_NOT_EXPOSE", str(ApprovedWorkflowRuns.public(result)))
        self.assertEqual(self.db["approved_visual_execution_slots"].docs[0]["expires_at"].year, 9999)
        another = {**deepcopy(self.document), "_id": "c" * 64, "run_id": "c" * 64}
        self.db["approved_workflow_runs"].docs.append(another)
        self.assertFalse(await self.worker(Transport()).once())

    async def test_dead_worker_known_session_reconciles_without_replay(self):
        expired = datetime.now(timezone.utc) - timedelta(seconds=1)
        run = self.db["approved_workflow_runs"].docs[0]
        run.update(state="running", execution_token="token", lease_expires_at=expired, remote_session_id="known-session")
        self.db["approved_visual_execution_slots"].docs.append({"_id": module.SLOT, "run_id": run["run_id"], "token": "token", "expires_at": datetime(9999, 1, 1, tzinfo=timezone.utc)})
        completed = {**deepcopy(self.document), "_id": "c" * 64, "run_id": "c" * 64, "state": "completed", "verdict": "blocked", "evidence": "keep"}
        self.db["approved_workflow_runs"].docs.append(completed)
        worker = self.worker(Transport())
        with patch.object(module, "close_remote", AsyncMock(return_value=True)) as close:
            await worker.reconcile()
        close.assert_awaited_once_with("known-session")
        self.assertEqual(run["reason"], "WORKER_INTERRUPTED")
        self.assertEqual(run["state"], "completed")
        self.assertEqual(self.db["approved_workflow_runs"].docs[1], completed)
        self.assertEqual(self.db["approved_visual_execution_slots"].docs, [])

    async def test_dead_worker_unknown_session_does_not_release_capacity(self):
        run = self.db["approved_workflow_runs"].docs[0]
        run.update(state="running", execution_token="token", lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
        slot = {"_id": module.SLOT, "run_id": run["run_id"], "token": "token", "expires_at": datetime(9999, 1, 1, tzinfo=timezone.utc)}
        self.db["approved_visual_execution_slots"].docs.append(slot)
        worker = self.worker(Transport())
        with patch.object(module, "close_remote", AsyncMock(return_value=False)):
            await worker.reconcile()
        self.assertEqual(run["state"], "completed")
        self.assertFalse(run["cleanup_confirmed"])
        self.assertEqual(self.db["approved_visual_execution_slots"].docs, [slot])

    async def test_feature_and_production_gates_stop_worker(self):
        worker = self.worker(Transport())
        settings.features.approved_workflow_worker = False
        with self.assertRaises(HTTPException): await worker.once()
        settings.features.approved_workflow_worker = True; settings.app_env = "production"
        with self.assertRaises(HTTPException): await worker.once()
        self.auth.assert_not_awaited()

    async def test_child_protocol_uses_private_stdin_not_arguments_or_inherited_secrets(self):
        writes = []
        lines = iter([b'{"event":"session","session_id":"fixture-session"}\n',
                      b'{"event":"result","browser_ready":true,"cleanup_confirmed":true,"reason":"ACTION_RUNTIME_NOT_ENABLED"}\n', b''])
        async def readline(): return next(lines)
        process = SimpleNamespace(returncode=0, pid=123, stdin=SimpleNamespace(write=writes.append, drain=AsyncMock(), close=lambda: None),
                                  stdout=SimpleNamespace(readline=readline), wait=AsyncMock(return_value=0))
        with patch.object(settings, "visual_runner_python", sys.executable), \
             patch.object(settings, "browserstack_access_key", "PRIVATE_STDIN_CANARY"), \
             patch.dict(os.environ, {"OPENAI_API_KEY": "INHERITED_SECRET_CANARY"}), \
             patch.object(module.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)) as launch:
            transport = module.IsolatedPreflight()
            self.assertTrue(await transport.run(self.document, AsyncMock(), AsyncMock()))
        self.assertNotIn("PRIVATE_STDIN_CANARY", str(launch.call_args.args))
        self.assertNotIn("INHERITED_SECRET_CANARY", str(launch.call_args.kwargs["env"]))
        self.assertNotIn("OPENAI_API_KEY", launch.call_args.kwargs["env"])
        self.assertEqual(json.loads(writes[0])["provider_credentials"]["access_key"], "PRIVATE_STDIN_CANARY")
        self.assertTrue(transport.cleanup_confirmed)

    async def test_explicit_reconciliation_requires_fence_and_preserves_verdict(self):
        from app.services.approved_visual_run import digest
        run = self.db["approved_workflow_runs"].docs[0]
        run.update(state="completed", verdict="needs_review", reason="REMOTE_CLEANUP_UNCONFIRMED", cleanup_confirmed=False,
                   execution_token="token", remote_session_id="fixture-session", manifest_digest=digest(run["manifest"], b"test"))
        lease = {"_id": module.SLOT, "run_id": run["run_id"], "token": "other-token"}
        self.db["approved_visual_execution_slots"].docs.append(lease)
        worker = self.worker(Transport())
        with patch.object(module, "close_remote", AsyncMock(return_value=True)) as close:
            with self.assertRaises(ValueError): await worker.reconcile_run(run["run_id"])
            close.assert_not_awaited()
            lease["token"] = "token"
            result = await worker.reconcile_run(run["run_id"])
        self.assertTrue(result["cleanup_confirmed"])
        self.assertEqual(result["verdict"], "needs_review")
        self.assertEqual(result["reason"], "REMOTE_CLEANUP_UNCONFIRMED")
        self.assertEqual(self.db["approved_visual_execution_slots"].docs, [])

    async def test_legacy_missing_session_needs_authoritative_cleanup_confirmation(self):
        for provider_state, expected in (("done", True), ("running", False), ("passed", False)):
            def handle(request):
                if request.method == "DELETE":
                    return httpx.Response(404, json={"status": 6, "value": {"message": "Session unavailable"}})
                return httpx.Response(200, json={"automation_session": {"status": provider_state, "reason": "CLIENT_STOPPED_SESSION"}})
            factory = httpx.AsyncClient
            with patch.object(module.httpx, "AsyncClient", side_effect=lambda **kwargs: factory(**kwargs, transport=httpx.MockTransport(handle))):
                self.assertEqual(await module.close_remote("fixture-session"), expected)

    async def test_timeout_or_forced_parent_cancellation_cleans_up(self):
        for failure in (TimeoutError(), asyncio.CancelledError()):
            self.db["approved_workflow_runs"].docs = [deepcopy(self.document)]
            transport = Transport(error=failure); worker = self.worker(transport)
            await worker.once()
            self.assertTrue(transport.closed)
            result = self.db["approved_workflow_runs"].docs[0]
            self.assertIn(result["state"], ("completed", "cancelled"))
            self.assertNotEqual(result["verdict"], "passed")
            self.assertEqual(self.db["approved_visual_execution_slots"].docs, [])
