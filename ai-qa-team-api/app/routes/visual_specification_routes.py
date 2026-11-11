from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.config import settings
from app.db.connection import db
from app.models.visual_specification import WorkflowDraft, SpecificationDraft, SpecificationPreviewSelection, CompiledSpecificationPreview
from app.routes.approved_visual_runs import require_development, actor_id
from app.services.visual_specifications import VisualSpecifications
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_member, require_project_admin
from app.utils.safe_validation_route import SafeValidationRoute

VersionId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
CaseId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
router = APIRouter(prefix="/projects/{project_id}/visual-specifications", tags=["Visual specifications"],
                   route_class=SafeValidationRoute,
                   dependencies=[Depends(feature_required("reusable_workflows")), Depends(require_development)])


def service():
    return VisualSpecifications(db, settings.jwt_secret_key.encode())


@router.get("/workflows")
async def workflows(project_id: str, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().workflows(project_id)


@router.post("/workflows", status_code=201)
async def create_workflow(project_id: str, payload: WorkflowDraft, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().create_workflow(project_id, actor_id(user), payload)


@router.post("/workflows/{version_id}/approve")
async def approve_workflow(project_id: str, version_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await service().approve_workflow(project_id, actor_id(user), version_id)


@router.get("/cases/{testcase_id}")
async def specification(project_id: str, testcase_id: CaseId, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().latest_specification(project_id, testcase_id)


@router.post("/cases/{testcase_id}", status_code=201)
async def create_specification(project_id: str, testcase_id: CaseId, payload: SpecificationDraft, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().create_specification(project_id, testcase_id, actor_id(user), payload)


@router.post("/cases/{testcase_id}/{version_id}/approve")
async def approve_specification(project_id: str, testcase_id: CaseId, version_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await service().approve_specification(project_id, testcase_id, actor_id(user), version_id)


@router.post("/cases/{testcase_id}/{version_id}/preview", response_model=CompiledSpecificationPreview, response_model_exclude_none=True)
async def preview_specification(project_id: str, testcase_id: CaseId, version_id: VersionId,
                                payload: SpecificationPreviewSelection, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().preview(project_id, testcase_id, version_id, payload)
