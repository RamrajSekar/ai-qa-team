from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response

from app.db.connection import db
from app.models.test_result import ManualResultInput, ManualExecutionInput
from app.routes.approved_visual_runs import actor_id
from app.services.test_results import TestResults
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_member
from app.utils.safe_validation_route import SafeValidationRoute

CaseId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
router = APIRouter(prefix="/projects/{project_id}/test-results", tags=["Manual test results"], route_class=SafeValidationRoute,
    dependencies=[Depends(feature_required("manual_test_results", "test_generation"))])


@router.get("")
async def summaries(project_id: str, response: Response, case_ids: str = Query(max_length=4050), user=Depends(get_current_user)):
    import re
    await require_project_member(project_id, user)
    ids = case_ids.split(",")
    if not 1 <= len(ids) <= 50 or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", item) for item in ids):
        raise HTTPException(422, "Supply up to 50 test case IDs.")
    response.headers["Cache-Control"] = "private, no-store"
    return await TestResults(db).summaries(project_id, ids)


@router.get("/cases/{testcase_id}")
async def history(project_id: str, testcase_id: CaseId, response: Response, skip: int = Query(0, ge=0, le=10000), user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await TestResults(db).history(project_id, testcase_id, skip)


@router.post("/cases/{testcase_id}", status_code=201)
async def record(project_id: str, testcase_id: CaseId, payload: ManualResultInput, response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await TestResults(db).record_manual(project_id, testcase_id, actor_id(user), payload, actor_name=user.get("name"))


@router.post("/executions", status_code=201)
async def create_execution(project_id: str, payload: ManualExecutionInput, response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await TestResults(db).create_execution(project_id, actor_id(user), payload)


@router.get("/executions")
async def executions(project_id: str, response: Response, skip: int = Query(0, ge=0, le=10000), user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await TestResults(db).executions(project_id, skip)


@router.get("/executions/{execution_id}")
async def execution(project_id: str, execution_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")], response: Response, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    response.headers["Cache-Control"] = "private, no-store"
    return await TestResults(db).execution(project_id, execution_id)
