from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.db.connection import db
from app.models.product_knowledge import KnowledgeSourceInput, KnowledgeDraft, ReviewStoryAnalysis
from app.routes.approved_visual_runs import actor_id
from app.services.ai.ai_configuration_service import public_error
from app.services.ai.ai_usage_policy import AIUsageError
from app.services.ai.base_provider import LLMProviderError
from app.services.product_knowledge import ProductKnowledge
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_admin, require_project_member
from app.utils.safe_validation_route import SafeValidationRoute

VersionId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
StoryId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["Product knowledge"],
                   route_class=SafeValidationRoute, dependencies=[Depends(feature_required("product_knowledge"))])


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
