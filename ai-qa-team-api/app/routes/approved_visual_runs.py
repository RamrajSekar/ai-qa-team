from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response

from app.config import settings
from app.db.connection import db
from app.models.approved_visual_run import (
    AdmittedVisualRun, ApproveVisualTest, ApprovedVisualPreview, ApprovedVisualTest,
    StartApprovedVisualRun, VisualRunSelection, VisualTestRunState,
)
from app.services.approved_visual_run import ApprovedVisualRuns
from app.services import approved_visual_execution
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_admin, require_project_member, user_id


async def require_development():
    if settings.app_env.lower() not in {'development', 'local', 'test'}:
        raise HTTPException(403, 'Synthetic approval and admission are development-only.')


router = APIRouter(
    prefix='/projects/{project_id}/approved-visual-runs',
    tags=['Approved Visual Run Admission'],
    dependencies=[Depends(feature_required('approved_visual_run_admission')), Depends(require_development)],
)


def service():
    return ApprovedVisualRuns(db, settings.jwt_secret_key.encode())


def actor_id(user):
    actor = user_id(user)
    if not actor:
        raise HTTPException(403, 'An account identity is required.')
    return actor


@router.post('/testcases/{testcase_id}/approve', response_model=ApprovedVisualTest, status_code=201)
async def approve(project_id: str, testcase_id: Annotated[str, Path(pattern=r'^[A-Za-z0-9_-]{1,80}$')],
                  payload: ApproveVisualTest, user=Depends(get_current_user)):
    await require_project_admin(project_id, user)
    return await service().approve(project_id, testcase_id, actor_id(user), payload)


@router.post('/preview', response_model=ApprovedVisualPreview)
async def preview(project_id: str, payload: VisualRunSelection, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().preview(project_id, payload)


@router.post('', response_model=AdmittedVisualRun, status_code=201)
async def admit(project_id: str, payload: StartApprovedVisualRun, user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().admit(project_id, actor_id(user), payload)


@router.get('/testcases/{testcase_id}', response_model=VisualTestRunState)
async def testcase_state(project_id: str, testcase_id: Annotated[str, Path(pattern=r'^[A-Za-z0-9_-]{1,80}$')],
                         user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().testcase_state(project_id, testcase_id)


@router.get('/{run_id}', response_model=AdmittedVisualRun)
async def status(project_id: str, run_id: Annotated[str, Path(pattern=r'^[0-9a-f]{64}$')],
                 user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().status(project_id, run_id)


@router.post('/{run_id}/cancel', response_model=AdmittedVisualRun)
async def cancel(project_id: str, run_id: Annotated[str, Path(pattern=r'^[0-9a-f]{64}$')],
                 user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await service().cancel(project_id, run_id)


@router.post('/{run_id}/start', response_model=AdmittedVisualRun, status_code=202,
             dependencies=[Depends(feature_required('approved_visual_run_execution'))])
async def launch(project_id: str, run_id: Annotated[str, Path(pattern=r'^[0-9a-f]{64}$')],
                 user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    return await approved_visual_execution.start(service(), project_id, run_id, user)


@router.get('/{run_id}/evidence')
async def evidence(project_id: str, run_id: Annotated[str, Path(pattern=r'^[0-9a-f]{64}$')],
                   user=Depends(get_current_user)):
    await require_project_member(project_id, user)
    doc = await db['approved_visual_runs'].find_one(
        {'project_id': project_id, '_id': run_id, 'run.evidence_available': True},
    )
    if not doc or not doc.get('evidence_png'):
        raise HTTPException(404, 'Screenshot not found.')
    return Response(doc['evidence_png'], media_type='image/png', headers={
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
    })
