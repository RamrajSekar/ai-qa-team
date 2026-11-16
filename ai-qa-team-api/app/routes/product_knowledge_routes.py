from typing import Annotated, Literal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, Request
from fastapi.responses import FileResponse

from app.db.connection import db
from app.models.product_knowledge import KnowledgeSourceInput, KnowledgeDraft, ReviewStoryAnalysis
from app.models.knowledge_training import TrainingStart, TrainingReview, TrainingExtract, TrainingSave, TrainingRebase
from app.models.requirement_context import RequirementDraft
from app.services.requirement_contexts import RequirementContexts
from app.models.story_knowledge_review import StoryKnowledgeReviewInput
from app.services.story_knowledge_review import StoryKnowledgeReview
from app.models.knowledge_ask import KnowledgeQuestion
from app.services.knowledge_ask import KnowledgeAsk
from app.services.knowledge_training import KnowledgeTraining
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


def training_service():
    return KnowledgeTraining(db, service())


@router.post("/ask", dependencies=[Depends(feature_required("knowledge_ask"))])
async def ask_knowledge(project_id: str, payload: KnowledgeQuestion, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await ai_result(KnowledgeAsk(db, service()).ask(project_id, user, payload))


@router.get("/training")
async def training_reviews(project_id: str, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await training_service().listing(project_id)


@router.post("/training", status_code=201)
async def start_training(project_id: str, payload: TrainingStart, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await training_service().start(project_id, actor_id(user), payload)


@router.get("/training/{review_id}")
async def training_review(project_id: str, review_id: VersionId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await training_service().get(project_id, review_id)


@router.post("/training/{review_id}/extract")
async def extract_training(project_id: str, review_id: VersionId, payload: TrainingExtract, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await ai_result(training_service().extract(project_id, user, review_id, payload))


@router.post("/training/{review_id}/review")
async def update_training_review(project_id: str, review_id: VersionId, payload: TrainingReview, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await training_service().review(project_id, review_id, payload)


@router.post("/training/{review_id}/save")
async def save_training_review(project_id: str, review_id: VersionId, payload: TrainingSave, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await training_service().save(project_id, actor_id(user), review_id, payload)


@router.post("/training/{review_id}/rebase")
async def rebase_training_review(project_id: str, review_id: VersionId, payload: TrainingRebase, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await training_service().rebase(project_id, actor_id(user), review_id, payload)


@router.post("/training/{review_id}/discard")
async def discard_training_review(project_id: str, review_id: VersionId, payload: TrainingSave, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await training_service().discard(project_id, actor_id(user), review_id, payload)


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
    result = await service().overview(project_id)
    # Display-only fallback for older approvals by the signed-in reviewer. Never
    # mutate historical receipts or substitute an untrusted client identity.
    for version in result["versions"]:
        if version.get("approved_by") == actor_id(user) and version.get("approved_by_name") in (None, "Project reviewer"):
            version["approved_by_name"] = user.get("name") or user.get("full_name") or user.get("email") or "Project reviewer"
    return result


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


@router.get("/sources/{source_id}")
async def source_evidence(project_id: str, source_id: VersionId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    knowledge = service()
    return knowledge.public(await knowledge.record("product_knowledge_sources", project_id, source_id))


@router.post("/versions", status_code=201)
async def create_version(project_id: str, payload: KnowledgeDraft, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().create_version(project_id, actor_id(user), payload)


@router.get("/versions/{version_id}")
async def knowledge_version(project_id: str, version_id: VersionId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    knowledge = service()
    return knowledge.public(await knowledge.record("product_knowledge_versions", project_id, version_id))


@router.post("/versions/{version_id}/approve")
async def approve(project_id: str, version_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await service().approve(project_id, actor_id(user), version_id,
        actor_name=user.get("name") or user.get("full_name") or user.get("email") or "Project reviewer")


@router.post("/stories/{story_id}/analyze", dependencies=[Depends(feature_required("story_analysis"))])
async def analyze(project_id: str, story_id: StoryId,
                  analysis_mode: Literal["story_only", "knowledge_aware"] | None = Query(default=None),
                  user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await ai_result(service().analyze(project_id, user, story_id, analysis_mode=analysis_mode))


@router.get("/stories/{story_id}/analysis", dependencies=[Depends(feature_required("story_analysis"))])
async def latest_analysis(project_id: str, story_id: StoryId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().latest_analysis(project_id, story_id)


@router.post("/stories/{story_id}/analysis/{analysis_id}/review", dependencies=[Depends(feature_required("story_analysis"))])
async def review_analysis(project_id: str, story_id: StoryId, analysis_id: VersionId,
                          payload: ReviewStoryAnalysis, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await service().review_analysis(project_id, actor_id(user), story_id, analysis_id, payload)


@router.get("/stories/{story_id}/requirements")
async def requirement_contexts(project_id: str, story_id: StoryId, user=Depends(get_current_user)):
    await require_project_member(project_id,user)
    return await RequirementContexts(db).listing(project_id,story_id)


@router.post("/stories/{story_id}/requirements")
async def create_requirements(project_id: str, story_id: StoryId, payload: RequirementDraft, user=Depends(get_current_user)):
    await require_project_member(project_id,user)
    return await RequirementContexts(db).create(project_id,story_id,actor_id(user),payload)


@router.get("/stories/{story_id}/requirements/{context_id}")
async def read_requirements(project_id: str, story_id: StoryId, context_id: VersionId, user=Depends(get_current_user)):
    await require_project_member(project_id,user)
    service=RequirementContexts(db);row=await service.row(project_id,story_id,context_id)
    return {**await service.view(row),"impact":await service.impact(row)}


@router.post("/stories/{story_id}/requirements/{context_id}/approve")
async def approve_requirements(project_id: str, story_id: StoryId, context_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id,user)
    return await RequirementContexts(db).approve(project_id,story_id,context_id,user)


@router.post("/stories/{story_id}/requirements/{context_id}/activate")
async def activate_requirements(project_id: str, story_id: StoryId, context_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id,user)
    return await RequirementContexts(db).activate(project_id,story_id,context_id,actor_id(user))


@router.get("/stories/{story_id}/change-reviews")
async def story_change_reviews(project_id: str, story_id: StoryId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await StoryKnowledgeReview(db).listing(project_id, story_id)


@router.post("/stories/{story_id}/change-reviews")
async def submit_story_change(project_id: str, story_id: StoryId, payload: StoryKnowledgeReviewInput, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await StoryKnowledgeReview(db).submit(project_id, story_id, actor_id(user), payload)


@router.post("/stories/{story_id}/change-reviews/{review_id}/approve")
async def approve_story_change(project_id: str, story_id: StoryId, review_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await StoryKnowledgeReview(db).approve(project_id, story_id, review_id, user)


@router.post("/stories/{story_id}/change-reviews/{review_id}/activate")
async def activate_story_change(project_id: str, story_id: StoryId, review_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await StoryKnowledgeReview(db).approve(project_id, story_id, review_id, user, activate=True)
