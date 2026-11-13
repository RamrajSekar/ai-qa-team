from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, Request
from fastapi.responses import FileResponse

from app.db.connection import db
from app.models.product_knowledge import KnowledgeSourceInput, KnowledgeDraft, ReviewStoryAnalysis
from app.routes.approved_visual_runs import actor_id
from app.services.ai.ai_configuration_service import public_error
from app.services.ai.ai_usage_policy import AIUsageError
from app.services.ai.base_provider import LLMProviderError
from app.services.product_knowledge import ProductKnowledge
from app.services.knowledge_ingestion import KnowledgeIngestion, UploadAdmission, PrivateDevelopmentStore
from app.config import settings
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_admin, require_project_member
from app.utils.safe_validation_route import SafeValidationRoute

VersionId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
StoryId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
async def private_response(response: Response):
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["Product knowledge"],
                   route_class=SafeValidationRoute, dependencies=[Depends(feature_required("product_knowledge")), Depends(private_response)])


def service():
    return ProductKnowledge(db)


async def ai_result(awaitable):
    try:
        return await awaitable
    except AIUsageError as exc:
        raise HTTPException(exc.status_code, exc.public_detail()) from None
    except LLMProviderError as exc:
        raise public_error(exc) from None


@router.get("")
async def overview(project_id: str, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().overview(project_id)


@router.get("/uploads")
async def uploads(project_id: str, response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    rows = await db["knowledge_ingestion_jobs"].find({"project_id": project_id}).sort("created_at", -1).limit(50).to_list(50)
    return {"records": [KnowledgeIngestion.public(row) for row in rows],
        "enabled": bool(settings.features.knowledge_uploads and settings.knowledge_ingestion.infrastructure_verified
            and settings.knowledge_ingestion.decoder_engine and settings.knowledge_ingestion.decoder_image
            and settings.knowledge_ingestion.storage_backend == "local_dev" and settings.knowledge_ingestion.allow_local_development
            and settings.app_env.lower() in {"development", "local", "test"}),
        "max_upload_bytes": settings.knowledge_ingestion.max_upload_bytes}


@router.post("/uploads", status_code=201, dependencies=[Depends(feature_required("knowledge_uploads"))])
async def admit_upload(project_id: str, payload: UploadAdmission, response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await KnowledgeIngestion(db).admit(project_id, user["email"], payload)


@router.put("/uploads/{upload_id}/content", dependencies=[Depends(feature_required("knowledge_uploads"))])
async def receive_upload(project_id: str, upload_id: VersionId, request: Request, response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    if request.headers.get("content-type", "").split(";")[0] != "application/octet-stream":
        raise HTTPException(415, "Upload content as application/octet-stream.")
    response.headers["Cache-Control"] = "private, no-store"
    return await KnowledgeIngestion(db).receive(project_id, upload_id, request.stream())


@router.get("/uploads/{upload_id}")
async def upload_status(project_id: str, upload_id: VersionId, response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return KnowledgeIngestion.public(await KnowledgeIngestion(db).row(project_id, upload_id))


@router.delete("/uploads/{upload_id}")
async def delete_upload(project_id: str, upload_id: VersionId, response: Response, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await KnowledgeIngestion(db).delete(project_id, upload_id)


@router.get("/uploads/{upload_id}/images/{image_id}")
async def upload_image(project_id: str, upload_id: VersionId, image_id: VersionId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    row = await KnowledgeIngestion(db).row(project_id, upload_id)
    if row["state"] == "deleted" or row["expires_at"] <= datetime.now(timezone.utc).isoformat() or not any(image["image_id"] == image_id for image in row.get("images", [])):
        raise HTTPException(404, "Image is unavailable.")
    path = PrivateDevelopmentStore().folder(project_id, upload_id) / (image_id + ".png")
    if not path.is_file() or path.is_symlink(): raise HTTPException(404, "Image is unavailable.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})


@router.get("/analysis-summaries", dependencies=[Depends(feature_required("story_analysis"))])
async def analysis_summaries(project_id: str, response: Response, story_ids: str = Query(max_length=8100), user=Depends(get_current_user)):
    import re
    await require_project_member(project_id, user)
    ids = story_ids.split(",")
    if not 1 <= len(ids) <= 100 or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity) for identity in ids):
        raise HTTPException(422, "Supply up to 100 story IDs.")
    response.headers["Cache-Control"] = "private, no-store"
    return await service().analysis_summaries(project_id, ids)


@router.post("/stories/{story_id}/suggest-knowledge")
async def suggest_from_story(project_id: str, story_id: StoryId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await ai_result(service().suggest_from_story(project_id, user, actor_id(user), story_id))


@router.post("/sources", status_code=201)
async def add_source(project_id: str, payload: KnowledgeSourceInput, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().add_source(project_id, actor_id(user), payload)


@router.post("/sources/{source_id}/extract")
async def extract(project_id: str, source_id: VersionId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await ai_result(service().extract(project_id, user, source_id))


@router.post("/versions", status_code=201)
async def create_version(project_id: str, payload: KnowledgeDraft, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().create_version(project_id, actor_id(user), payload)


@router.post("/versions/{version_id}/approve")
async def approve(project_id: str, version_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await service().approve(project_id, actor_id(user), version_id)


@router.post("/stories/{story_id}/analyze", dependencies=[Depends(feature_required("story_analysis"))])
async def analyze(project_id: str, story_id: StoryId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await ai_result(service().analyze(project_id, user, story_id))


@router.get("/stories/{story_id}/analysis", dependencies=[Depends(feature_required("story_analysis"))])
async def latest_analysis(project_id: str, story_id: StoryId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().latest_analysis(project_id, story_id)


@router.post("/stories/{story_id}/analysis/{analysis_id}/review", dependencies=[Depends(feature_required("story_analysis"))])
async def review_analysis(project_id: str, story_id: StoryId, analysis_id: VersionId,
                          payload: ReviewStoryAnalysis, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await service().review_analysis(project_id, actor_id(user), story_id, analysis_id, payload)
