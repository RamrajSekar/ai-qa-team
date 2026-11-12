from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Response

from app.db.connection import db
from app.models.test_design_review import TestDesignDraft
from app.routes.approved_visual_runs import actor_id
from app.services.test_design_review import TestDesignReview
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_member, require_project_admin
from app.utils.safe_validation_route import SafeValidationRoute

CaseId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
VersionId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
router = APIRouter(prefix="/projects/{project_id}/test-design", tags=["Test design review"], route_class=SafeValidationRoute,
    dependencies=[Depends(feature_required("test_generation", "product_knowledge", "story_analysis"))])


@router.get("/cases/{testcase_id}")
async def state(project_id: str, testcase_id: CaseId, response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await TestDesignReview(db).state(project_id, testcase_id)


@router.post("/cases/{testcase_id}", status_code=201)
async def create(project_id: str, testcase_id: CaseId, payload: TestDesignDraft, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await TestDesignReview(db).create(project_id, testcase_id, actor_id(user), payload)


@router.post("/cases/{testcase_id}/{version_id}/approve")
async def approve(project_id: str, testcase_id: CaseId, version_id: VersionId, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await TestDesignReview(db).approve(project_id, testcase_id, actor_id(user), version_id)


@router.get("/cases/{testcase_id}/{version_id}/export")
async def export(project_id: str, testcase_id: CaseId, version_id: VersionId, response: Response,
                 format: Literal["json", "text"] = "json", user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return await TestDesignReview(db).export(project_id, testcase_id, version_id, format)
