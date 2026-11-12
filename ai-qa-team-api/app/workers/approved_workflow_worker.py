"""Explicitly launched development worker. No API lifespan hook, legacy queue or replay."""
import asyncio
import argparse
from datetime import datetime, timedelta, timezone
import json
import hmac
import os
from pathlib import Path
import re
import signal
from uuid import uuid4

import httpx
from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.services.approved_workflow_runs import ApprovedWorkflowRuns
from app.services.approved_visual_run import digest
from app.utils.feature_flags import require_features
from app.utils.project_authorization import require_project_member

# Shares the existing BrowserStack development slot, not its job consumer.
SLOT = "browserstack-synthetic-v1"
RUN_SECONDS = 80
# Detect a dead supervisor after work/cleanup budgets. Unconfirmed remote sessions
# hold capacity until confirmed cleanup, never merely until a guessed idle expiry.
LEASE_SECONDS = 120
RUNNER = Path(__file__).resolve().parents[3] / "visual-runner" / "workflow_preflight.py"
SESSION = re.compile(r"^[A-Za-z0-9-]{1,128}$")


class Stopped(Exception):
    pass


async def close_remote(identity):
    if not isinstance(identity, str) or not SESSION.fullmatch(identity):
        return False
    try:
        async with httpx.AsyncClient(auth=(settings.browserstack_username, settings.browserstack_access_key),
                timeout=httpx.Timeout(3, read=5), trust_env=False) as client:
            response = await client.delete("https://hub-cloud.browserstack.com/wd/hub/session/" + identity)
            value = response.json().get("value")
            error = value.get("error") if isinstance(value, dict) else None
            if (response.is_success and not error) or error == "invalid session id":
                return True
            # BrowserStack can return a legacy JSON Wire 404 without W3C's error
            # field when the child already quit. Confirm closure via its read-only
            # session API; an arbitrary 404 is not proof of cleanup.
            details = await client.get("https://api.browserstack.com/automate/sessions/" + identity + ".json")
            session = details.json().get("automation_session", {})
            return (details.is_success and session.get("status") == "done"
                    and session.get("reason") == "CLIENT_STOPPED_SESSION")
    except Exception:
        return False


async def authorize(database, document):
    identity = document.get("dispatch_requested_by")
    if not isinstance(identity, str) or not identity:
        raise HTTPException(403, "Dispatch identity required")
    choices = [{"id": identity}, {"_id": identity}]
    if ObjectId.is_valid(identity):
        choices.append({"_id": ObjectId(identity)})
    user = await database["users"].find_one({"$or": choices})
    if not user or user.get("disabled") or not user.get("email"):
        raise HTTPException(403, "Dispatch account unavailable")
    await require_project_member(document["project_id"], user)


class IsolatedPreflight:
    """Private stdin/event protocol; inherited backend secrets are excluded."""
    def __init__(self):
        self.process = None
        self.session = None
        self.result = None
        self.cleanup_confirmed = True

    async def run(self, document, checkpoint, session_event):
        python = settings.visual_runner_python
        if not python or not Path(python).is_file() or not RUNNER.is_file():
            raise RuntimeError("RUNNER_NOT_CONFIGURED")
        env = {key: os.environ[key] for key in ("SystemRoot", "SystemDrive", "TEMP", "TMP") if key in os.environ}
        self.process = await asyncio.create_subprocess_exec(python, "-I", str(RUNNER),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            env=env, cwd=str(RUNNER.parent), limit=8192)
        self.cleanup_confirmed = False
        payload = {"operation": "browser-readiness-v1", "adapter": "browserstack-direct-webdriver-v1",
            "manifest_digest": document["manifest_digest"], "manifest": document["manifest"],
            "provider_credentials": {"username": settings.browserstack_username, "access_key": settings.browserstack_access_key}}
        self.process.stdin.write((json.dumps(payload) + "\n").encode())
        await self.process.stdin.drain()
        self.process.stdin.close()
        pending = asyncio.create_task(self.process.stdout.readline())
        try:
            while True:
                await checkpoint()
                done, _ = await asyncio.wait({pending}, timeout=0.25)
                if not done:
                    continue  # Queue/cancel polling, never a browser-workflow retry.
                line = pending.result()
                if not line:
                    break
                event = json.loads(line)
                if event.get("event") == "session" and self.session is None:
                    identity = event.get("session_id")
                    if not isinstance(identity, str) or not SESSION.fullmatch(identity):
                        raise ValueError("Invalid private session event")
                    self.session = identity
                    await session_event(identity)
                elif event.get("event") == "result" and self.result is None:
                    if (type(event.get("browser_ready")) is not bool or type(event.get("cleanup_confirmed")) is not bool
                            or event.get("reason") not in ("ACTION_RUNTIME_NOT_ENABLED", "BROWSER_PREFLIGHT_FAILED")):
                        raise ValueError("Invalid result event")
                    self.result = event
                else:
                    raise ValueError("Unexpected runner event")
                pending = asyncio.create_task(self.process.stdout.readline())
            await self.process.wait()
            if not self.result:
                raise RuntimeError("RUNNER_RESULT_MISSING")
            if self.result["browser_ready"] and self.session is None:
                raise RuntimeError("RUNNER_SESSION_EVENT_MISSING")
            if self.process.returncode != 0 and self.result["browser_ready"]:
                raise RuntimeError("RUNNER_RESULT_INCONSISTENT")
            self.cleanup_confirmed = self.result["cleanup_confirmed"]
            return self.result["browser_ready"]
        finally:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)

    async def close(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 3)
            except TimeoutError:
                self.process.kill()
                await asyncio.wait_for(self.process.wait(), 3)
        if self.session and not self.cleanup_confirmed:
            self.cleanup_confirmed = await close_remote(self.session)
        return self.cleanup_confirmed


class WorkflowWorker:
    def __init__(self, database, key, transport_factory=IsolatedPreflight, authorizer=authorize):
        self.db = database
        self.service = ApprovedWorkflowRuns(database, key)
        self.transport_factory = transport_factory
        self.authorizer = authorizer

    @staticmethod
    def enabled():
        require_features("reusable_workflows", "approved_visual_run_admission", "approved_workflow_worker")
        if settings.app_env not in ("development", "dev", "test", "local"):
            raise HTTPException(403, "Development worker only")

    async def reconcile_run(self, run_id):
        """Explicit maintenance for a terminated/stale owned session; never replay."""
        self.enabled()
        if not re.fullmatch(r"[0-9a-f]{64}", run_id):
            raise ValueError("Invalid run identity")
        runs = self.db["approved_workflow_runs"]
        document = await runs.find_one({"_id": run_id, "operation": "browser-readiness-v1"})
        if not document or not hmac.compare_digest(document["manifest_digest"], digest(document["manifest"], self.service.key)):
            raise ValueError("Owned manifest integrity required")
        if document.get("cleanup_confirmed"):
            return self.service.public(document)
        expiry = document.get("lease_expires_at")
        if isinstance(expiry, datetime) and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if document["state"] in ("running", "cancelling") and (not expiry or expiry > datetime.now(timezone.utc)):
            raise ValueError("Active lease must be cancelled through its service first")
        lease = {"_id": SLOT, "run_id": run_id, "token": document.get("execution_token")}
        if not await self.db["approved_visual_execution_slots"].find_one(lease):
            raise ValueError("Owned slot required")
        if await close_remote(document.get("remote_session_id")):
            fields = {"cleanup_confirmed": True, "cleanup_reconciled_at": datetime.now(timezone.utc).isoformat()}
            if document["state"] in ("running", "cancelling"):
                fields.update({"state": "cancelled" if document["state"] == "cancelling" else "completed",
                    "verdict": "cancelled" if document["state"] == "cancelling" else "blocked", "reason": "WORKER_INTERRUPTED"})
            await runs.update_one({"_id": run_id, "execution_token": document.get("execution_token")}, {"$set": fields})
            await self.db["approved_visual_execution_slots"].delete_one(lease)
        return self.service.public(await runs.find_one({"_id": run_id}))

    async def reconcile(self):
        now = datetime.now(timezone.utc)
        runs = self.db["approved_workflow_runs"]
        # No replay or requeue. An unknown remote session keeps the shared slot.
        for state in ("running", "cancelling"):
            while True:
                changed = await runs.find_one_and_update({"state": state, "lease_expires_at": {"$lte": now}},
                    {"$set": {"state": "cancelled" if state == "cancelling" else "completed",
                        "verdict": "cancelled" if state == "cancelling" else "blocked", "reason": "WORKER_INTERRUPTED",
                        "cleanup_confirmed": False, "finished_at": now.isoformat()}}, return_document=ReturnDocument.AFTER)
                if not changed:
                    break
                slot = {"_id": SLOT, "run_id": changed["run_id"], "token": changed["execution_token"]}
                if await close_remote(changed.get("remote_session_id")):
                    await runs.update_one({"_id": changed["_id"], "execution_token": changed["execution_token"]},
                        {"$set": {"cleanup_confirmed": True}})
                    await self.db["approved_visual_execution_slots"].delete_one(slot)

    async def once(self):
        self.enabled()
        await self.reconcile()
        candidate = await self.db["approved_workflow_runs"].find_one({"state": "queued", "operation": "browser-readiness-v1"}, sort=[("queued_at", 1)])
        if not candidate:
            return False
        slots = self.db["approved_visual_execution_slots"]
        now = datetime.now(timezone.utc)
        await slots.delete_one({"_id": SLOT, "expires_at": {"$lte": now}})
        token = uuid4().hex
        expiry = now + timedelta(seconds=LEASE_SECONDS)
        lease = {"_id": SLOT, "run_id": candidate["run_id"], "token": token}
        try:
            # The old synthetic adapter respects this same slot. It must not reclaim
            # a crashed remote session simply because the worker lease expired.
            await slots.insert_one({**lease, "expires_at": datetime(9999, 1, 1, tzinfo=timezone.utc)})
        except DuplicateKeyError:
            await self.db["approved_workflow_runs"].update_one({"_id": candidate["_id"], "state": "queued"},
                {"$set": {"reason": "BROWSER_SLOT_BUSY"}})
            return False
        runs = self.db["approved_workflow_runs"]
        claimed = None
        transport = None
        cleanup = True
        ready = False
        reason = "BROWSER_PREFLIGHT_FAILED"
        try:
            claimed = await runs.find_one_and_update({"_id": candidate["_id"], "project_id": candidate["project_id"], "state": "queued"},
                {"$set": {"state": "running", "execution_token": token, "lease_expires_at": expiry,
                    "started_at": now.isoformat(), "reason": "BROWSER_PREFLIGHT_RUNNING"}}, return_document=ReturnDocument.AFTER)
            if not claimed:
                return False
            query = {"_id": claimed["_id"], "project_id": claimed["project_id"], "execution_token": token}

            async def checkpoint():
                self.enabled()
                if not await runs.find_one({**query, "state": "running"}):
                    raise Stopped()
                if not await slots.find_one(lease):
                    raise Stopped()

            async def session_event(identity):
                await runs.update_one({**query, "state": "running"}, {"$set": {"remote_session_id": identity}})

            await self.authorizer(self.db, claimed)
            await self.service.validate_current(claimed)
            await checkpoint()
            if not settings.browserstack_username or not settings.browserstack_access_key:
                reason = "BROWSER_PROVIDER_NOT_CONFIGURED"
            else:
                transport = self.transport_factory()
                async with asyncio.timeout(RUN_SECONDS):
                    ready = await transport.run(claimed, checkpoint, session_event)
                reason = "ACTION_RUNTIME_NOT_ENABLED" if ready else "BROWSER_PREFLIGHT_FAILED"
        except (Stopped, asyncio.CancelledError):
            reason = "PREFLIGHT_CANCELLED"
        except TimeoutError:
            reason = "BROWSER_PREFLIGHT_TIMEOUT"
        except HTTPException:
            reason = "DISPATCH_INPUTS_OR_ACCESS_CHANGED"
        except RuntimeError as exc:
            allowed = {"RUNNER_NOT_CONFIGURED", "RUNNER_RESULT_MISSING", "RUNNER_SESSION_EVENT_MISSING", "RUNNER_RESULT_INCONSISTENT"}
            reason = str(exc) if str(exc) in allowed else "BROWSER_PREFLIGHT_FAILED"
        except Exception:
            reason = "BROWSER_PREFLIGHT_FAILED"
        finally:
            if transport:
                try:
                    cleanup = await asyncio.wait_for(transport.close(), 18)
                except BaseException:
                    cleanup = False
            if claimed:
                query = {"_id": claimed["_id"], "project_id": claimed["project_id"], "execution_token": token}
                current = await runs.find_one(query)
                cancelled = reason == "PREFLIGHT_CANCELLED" or (current and current["state"] == "cancelling")
                fields = {"state": "cancelled" if cancelled else "completed", "verdict": "cancelled" if cancelled else "blocked",
                    "browser_readiness": "ready" if ready else "not_ready", "cleanup_confirmed": cleanup,
                    "reason": reason if cleanup else "REMOTE_CLEANUP_UNCONFIRMED", "finished_at": datetime.now(timezone.utc).isoformat()}
                if not cleanup and not cancelled:
                    fields["verdict"] = "needs_review"
                # Cancellation wins a completion race through per-state compare-and-set.
                for state in ("running", "cancelling"):
                    final = {**fields, **({"state": "cancelled", "verdict": "cancelled",
                        "reason": "PREFLIGHT_CANCELLED" if cleanup else "REMOTE_CLEANUP_UNCONFIRMED"} if state == "cancelling" else {})}
                    await runs.update_one({**query, "state": state}, {"$set": final})
            if cleanup:
                await slots.delete_one(lease)
        return claimed is not None


async def main(once=False, reconcile_run=None):
    from app.db.connection import db
    worker = WorkflowWorker(db, settings.jwt_secret_key.encode())
    worker.enabled()
    if reconcile_run:
        result = await worker.reconcile_run(reconcile_run)
        print(json.dumps({key: result.get(key) for key in ("run_id", "state", "reason", "cleanup_confirmed")}))
        return
    print("Development browser-readiness worker started; approved test actions are not executed.", flush=True)
    if once:
        await worker.once()
        return
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    active = asyncio.current_task()
    def stopping(*_):
        loop.call_soon_threadsafe(stop.set)
        loop.call_soon_threadsafe(active.cancel)
    signal.signal(signal.SIGINT, stopping)
    signal.signal(signal.SIGTERM, stopping)
    try:
        while not stop.is_set():
            await worker.once()
            if not stop.is_set():
                await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Consume at most one queued readiness operation, then exit")
    mode.add_argument("--reconcile-run", help="Confirm cleanup of an owned terminal/stale run; never replay it")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.once, args.reconcile_run))
    except Exception:
        raise SystemExit("Workflow worker stopped; inspect sanitized run status.") from None
