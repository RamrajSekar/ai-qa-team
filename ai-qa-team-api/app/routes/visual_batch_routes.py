from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.models.visual_batch_model import BatchRun, BatchStart
from app.services.visual_batch_service import ARTIFACTS, guard, local_path, public, visual_batches
from app.services.visual_batch_engine import EngineError
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_member

router = APIRouter(prefix='/projects/{project_id}/visual-lab/batches', tags=['Visual Runner Batches'],
    dependencies=[Depends(feature_required('visual_runner_lab', 'visual_runner_batches'))])


async def authorize(project_id: str, user=Depends(get_current_user)):
    guard()
    project, membership = await require_project_member(project_id, user)
    return user, project


@router.post('', response_model=BatchRun, status_code=202)
async def start(project_id: str, payload: BatchStart, auth=Depends(authorize)):
    user, project = auth
    owner = project.get('created_by')
    if not owner:
        raise HTTPException(409, 'Project billing ownership needs review.')
    try:
        return await visual_batches.enqueue(project_id, user, owner, payload)
    except EngineError:
        raise HTTPException(503, 'Local batch dispatcher unavailable.') from None


@router.get('', response_model=list[BatchRun])
async def recent(project_id: str, auth=Depends(authorize)):
    docs = await visual_batches.db['visual_batches'].find({'project_id': project_id}).sort('created_at', -1).limit(20).to_list(20)
    return [public(doc) for doc in docs]


@router.get('/{batch_id}', response_model=BatchRun)
async def status(project_id: str, batch_id: str, auth=Depends(authorize)):
    return await visual_batches.get(project_id, batch_id)


@router.post('/{batch_id}/cancel', response_model=BatchRun)
async def cancel(project_id: str, batch_id: str, auth=Depends(authorize)):
    return await visual_batches.cancel(project_id, batch_id)


@router.get('/{batch_id}/cases/{case_id}/artifacts/{artifact_id}')
async def artifact(project_id: str, batch_id: str, case_id: str, artifact_id: str, auth=Depends(authorize)):
    run = await visual_batches.get(project_id, batch_id)
    case = next((c for c in run.cases if c.case_run_id == case_id), None)
    if case is None or artifact_id not in ARTIFACTS or artifact_id not in case.screenshots:
        raise HTTPException(404, 'Screenshot not found')
    root = local_path(batch_id)
    folder = root / case.case_run_id
    path = folder / (artifact_id + '.png')
    if folder.is_symlink() or path.is_symlink() or path.resolve().parent != folder.resolve() or not path.is_file():
        raise HTTPException(404, 'Screenshot not found')
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
