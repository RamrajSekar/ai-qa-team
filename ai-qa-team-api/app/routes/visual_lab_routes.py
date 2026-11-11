from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.db.connection import db
from app.models.visual_lab_model import VisualLabRun, VisualLabStart
from app.services.visual_lab_service import ARTIFACTS, guard, visual_lab, workspace
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_member

router = APIRouter(prefix='/projects/{project_id}/visual-lab', tags=['Visual Runner Lab'],
                   dependencies=[Depends(feature_required('visual_runner_lab'))])


async def authorize(project_id: str, current_user=Depends(get_current_user)):
    guard()
    await require_project_member(project_id, current_user)
    return current_user


@router.post('/runs', response_model=VisualLabRun, status_code=202)
async def start(project_id: str, payload: VisualLabStart, user=Depends(authorize)):
    return await visual_lab.start(project_id, user, payload.headed)


@router.get('/runs', response_model=list[VisualLabRun])
async def recent(project_id: str, user=Depends(authorize)):
    docs = await db['visual_lab_runs'].find({'project_id': project_id}).sort('created_at', -1).limit(10).to_list(10)
    return [await visual_lab.reconcile(doc['run_id'], project_id) for doc in docs]


@router.get('/runs/{run_id}', response_model=VisualLabRun)
async def status(project_id: str, run_id: str, user=Depends(authorize)):
    workspace(run_id)  # Strict ID syntax, even before lookup.
    return await visual_lab.reconcile(run_id, project_id)


@router.post('/runs/{run_id}/cancel', response_model=VisualLabRun)
async def cancel(project_id: str, run_id: str, user=Depends(authorize)):
    workspace(run_id)
    return await visual_lab.cancel(run_id, project_id)


@router.get('/runs/{run_id}/artifacts/{artifact_id}')
async def artifact(project_id: str, run_id: str, artifact_id: str, user=Depends(authorize)):
    run = await visual_lab.reconcile(run_id, project_id)
    if artifact_id not in ARTIFACTS or artifact_id not in run.screenshots:
        raise HTTPException(404, 'Screenshot not found')
    path = workspace(run_id) / f'{artifact_id}.png'
    if path.is_symlink() or path.resolve().parent != workspace(run_id).resolve() or not path.is_file():
        raise HTTPException(404, 'Screenshot not found')
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
