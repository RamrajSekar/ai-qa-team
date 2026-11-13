"""Explicit standalone development worker. API startup never starts this worker.

Run once per bounded job on a qualified Linux processing host. Expired leases are
blocked for review, never replayed; a provider call may have completed remotely.
"""
import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from pymongo import ReturnDocument
from app.config import settings
from app.db.connection import db
from app.models.product_knowledge import KnowledgeSourceInput
from app.services.ai.ai_usage_policy import AIOperation
from app.services.ai.ai_usage_service import AIUsageService
from app.services.ai.base_provider import LLMRequest
from app.services.ingestion_gateway import IngestionGateway
from app.services.knowledge_ingestion import KnowledgeIngestion, PrivateDevelopmentStore, DecodedOutput
from app.services.product_knowledge import ProductKnowledge
from app.services.prompt_registry_service import get_active
from app.utils.project_authorization import require_project_member
from app.utils.feature_flags import require_features


def decoder_command(config, folder, identity, uid, gid):
    import re
    if uid == 0 or gid == 0: raise RuntimeError("NON_ROOT_WORKER_REQUIRED")
    if not re.fullmatch(r"[0-9a-f]{32}",identity): raise RuntimeError("INVALID_JOB_ID")
    if not config.decoder_engine or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{1,240}",config.decoder_image): raise RuntimeError("DECODER_NOT_CONFIGURED")
    if any(char in str(folder) for char in [",","\n","\r"]): raise RuntimeError("INVALID_WORKSPACE")
    return [config.decoder_engine,"run","--rm","--pull=never","--name","qa-knowledge-"+identity,
        "--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",
        "--memory","1g","--cpus","2","--pids-limit","128","--user",f"{uid}:{gid}",
        "--tmpfs","/tmp:rw,noexec,nosuid,size=64m","--mount",f"type=bind,src={folder},dst=/work",
        "--workdir","/work","-i",config.decoder_image]


async def decode(folder, job):
    if os.name != "posix": raise RuntimeError("LINUX_PROCESSING_REQUIRED")
    config = settings.knowledge_ingestion
    command=decoder_command(config,folder,job["upload_id"],os.getuid(),os.getgid())
    payload={"workspace":"/work","format":job["format"],"max_bytes":config.max_upload_bytes,
        "max_pages":config.max_pages,"max_images":config.max_images,"interpret_images":job["interpret_images"]}
    output_file=(folder/"result.json").open("wb")
    try:
        process=await asyncio.create_subprocess_exec(*command,stdin=asyncio.subprocess.PIPE,stdout=output_file,
            stderr=asyncio.subprocess.DEVNULL,start_new_session=True,
            env={"PATH":"/usr/local/bin:/usr/bin:/bin","LANG":"C.UTF-8"})
    except BaseException:
        output_file.close();raise
    communication=asyncio.create_task(process.communicate(json.dumps(payload).encode()))
    started=asyncio.get_running_loop().time()
    try:
        while not communication.done():
            if (folder/"cancel").exists(): raise RuntimeError("CANCELLED")
            if asyncio.get_running_loop().time()-started>config.processing_timeout_seconds: raise RuntimeError("DECODER_TIMEOUT")
            await asyncio.wait({communication},timeout=0.25)
        await communication;output_file.close()
        if process.returncode or (folder/"result.json").stat().st_size>1000000: raise RuntimeError("DECODING_FAILED")
        result=json.loads((folder/"result.json").read_bytes())
        if result.get("error_code"): raise RuntimeError("DECODING_FAILED")
        return result
    finally:
        output_file.close()
        # Only the container named for this server-owned job is targeted.
        cleanup_failed=False
        try:
            cleanup=await asyncio.create_subprocess_exec(config.decoder_engine,"rm","--force","qa-knowledge-"+job["upload_id"],
                stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,
                env={"PATH":"/usr/local/bin:/usr/bin:/bin","LANG":"C.UTF-8"})
            try: await asyncio.wait_for(cleanup.wait(),timeout=10)
            except asyncio.TimeoutError:
                cleanup_failed=True;cleanup.kill();await cleanup.wait()
        except OSError: cleanup_failed=True
        finally:
            if process.returncode is None:
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            await process.wait()
            if not communication.done():
                communication.cancel();await asyncio.gather(communication,return_exceptions=True)
        if cleanup_failed: raise RuntimeError("DECODER_CLEANUP_UNCONFIRMED")



async def process_job(database, job, user, store, decoder=decode, usage_factory=AIUsageService):
    require_features("product_knowledge", "knowledge_uploads")
    if job["format"] not in {"txt","pdf","docx"}: raise RuntimeError("DOCUMENT_FORMAT_UNSUPPORTED")
    if job["interpret_images"]: require_features("knowledge_image_interpretation")
    if job["interpret_images"] and not job["consent_ai"]: raise RuntimeError("AI_CONSENT_REQUIRED")
    folder = store.folder(job["project_id"],job["upload_id"])
    async def checkpoint():
        current=await database["knowledge_ingestion_jobs"].find_one({"project_id":job["project_id"],"upload_id":job["upload_id"],"state":"processing","delete_requested":False,"lease_owner":job["lease_owner"]})
        if not current or (folder/"cancel").exists(): raise RuntimeError("CANCELLED")
    await checkpoint()
    decoded = await decoder(folder,job)
    await checkpoint()
    decoded = DecodedOutput.model_validate(decoded).model_dump(exclude_none=True)
    if sum(len(page["text"]) for page in decoded["pages"]) > 60000: raise RuntimeError("TEXT_LIMIT")
    if decoded["images"] and (not job["interpret_images"] or len(decoded["images"])>settings.knowledge_ingestion.max_images): raise RuntimeError("INVALID_DECODER_OUTPUT")
    if job["format"]=="pdf" and len(decoded["pages"])>settings.knowledge_ingestion.max_pages: raise RuntimeError("INVALID_DECODER_OUTPUT")
    pending = []
    for page in decoded["pages"]:
        if page["text"].strip():
            pending.append((KnowledgeSourceInput(title=f"{job['title']} — {('page '+str(page['page'])) if 'page' in page else ('block '+str(page['block']))}"[:240],kind="document",text=page["text"]),
                {"upload_id":job["upload_id"],"kind":"document","page_number":page.get("page"),"block_number":page.get("block")}))
    for image in decoded["images"]:
        await checkpoint()
        import re
        if not re.fullmatch(r"[0-9a-f]{32}", image["image_id"]): raise RuntimeError("INVALID_IMAGE_ID")
        image_path=folder/(image["image_id"]+".png")
        if image_path.is_symlink() or image_path.resolve().parent != folder or image_path.stat().st_size>2000000: raise RuntimeError("IMAGE_LIMIT")
        payload=image_path.read_bytes()
        if payload[:8]!=b'\x89PNG\r\n\x1a\n': raise RuntimeError("INVALID_IMAGE")
        prompt=await get_active("MEDIA_IMAGE_OBSERVATION_V1",database=database)
        response=await usage_factory(database=database,gateway=IngestionGateway(payload)).execute(AIOperation.MEDIA_IMAGE_OBSERVATION,job["project_id"],user,
            LLMRequest(prompt="Describe supplied visible product content only. This is an unapproved observation.",system_prompt=prompt["system_prompt"],prompt_key=prompt["prompt_key"],prompt_version=str(prompt["resolved_version"]),max_tokens=1000))
        text=response.text.strip()
        if not text or len(text)>8000: raise RuntimeError("IMAGE_OBSERVATION_LIMIT")
        pending.append((KnowledgeSourceInput(title=(job["title"]+" — image observation")[:240],kind="document",text=text),
            {"kind":"image_observation","upload_id":job["upload_id"],**image,"page_number":image.get("page"),"prompt_key":prompt["prompt_key"],"prompt_version":prompt["resolved_version"]}))
    await checkpoint()
    if not pending: raise RuntimeError("NO_READABLE_CONTENT")
    await require_project_member(job["project_id"],user)
    sources=[]
    for payload,origin in pending:
        source=await ProductKnowledge(database).add_source(job["project_id"],job["requested_by"],payload,origin=origin)
        sources.append(source["source_id"])
    return {"source_ids":sources,"images":decoded["images"]}


async def once(purge_only=False):
    now=datetime.now(timezone.utc)
    jobs=db["knowledge_ingestion_jobs"]
    await KnowledgeIngestion(db).reconcile_and_expire(now)
    if purge_only: return
    store=KnowledgeIngestion.guard()
    owner=uuid4().hex
    job=await jobs.find_one_and_update({"state":"queued","delete_requested":False},{"$set":{"state":"processing","lease_owner":owner,"lease_expires_at":(now+timedelta(minutes=15)).isoformat()}},return_document=ReturnDocument.AFTER)
    if not job: return
    try:
        user=await db["users"].find_one({"email":job["requested_by"]})
        if not user: raise RuntimeError("ACTOR_UNAVAILABLE")
        await require_project_member(job["project_id"],user)
        result=await asyncio.wait_for(process_job(db,job,user,store),timeout=600)
        await jobs.update_one({"_id":job["_id"],"state":"processing","lease_owner":owner,"delete_requested":False},{"$set":{"state":"ready",**result}})
    except BaseException as failure:
        # Never store exception text, process arguments, parser output or provider responses.
        allowed={"CANCELLED","DECODER_TIMEOUT","LINUX_PROCESSING_REQUIRED","DECODER_NOT_CONFIGURED","NO_READABLE_CONTENT","DECODING_FAILED","IMAGE_LIMIT","INVALID_IMAGE","INVALID_TIMESTAMPS","TRANSCRIPT_LIMIT","TEXT_LIMIT","DURATION_LIMIT","INVALID_DECODER_OUTPUT"}
        code=str(failure) if isinstance(failure,RuntimeError) and str(failure) in allowed else "PROCESSING_NOT_CONFIRMED"
        await jobs.update_one({"_id":job["_id"],"state":"processing","lease_owner":owner},{"$set":{"state":"blocked","error_code":code}})
        if isinstance(failure,(KeyboardInterrupt,SystemExit,asyncio.CancelledError)): raise
    finally:
        current=await jobs.find_one({"_id":job["_id"]})
        if current and current.get("delete_requested"):
            await jobs.update_one({"_id":job["_id"],"lease_owner":owner},{"$set":{"state":"blocked"}})
            await KnowledgeIngestion(db).delete(job["project_id"],job["upload_id"])


if __name__ == "__main__":
    if len(sys.argv)>2 or (len(sys.argv)==2 and sys.argv[1]!="--purge-only"):
        raise SystemExit("Only --purge-only is supported.")
    asyncio.run(once(purge_only="--purge-only" in sys.argv))
