from fastapi import APIRouter, Depends, HTTPException

from app.models.test_intent_model import BugInterpretRequest, BugInterpretResponse
from app.services.bug_interpreter import BugInterpretationError, BugInterpreter
from app.utils.auth_dependency import get_current_user
from app.utils.project_authorization import require_project_member


router = APIRouter(prefix="/projects/{project_id}/bugs", tags=["Bug Interpretation"])


@router.post("/interpret", response_model=BugInterpretResponse)
async def interpret_bug(project_id: str, payload: BugInterpretRequest, current_user=Depends(get_current_user)):
    await require_project_member(project_id, current_user)
    try:
        return await BugInterpreter().interpret(project_id, current_user, payload.bug_text)
    except BugInterpretationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.public_detail()) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "BUG_INTERPRETATION_FAILED", "message": "The bug could not be interpreted."},
        ) from None
