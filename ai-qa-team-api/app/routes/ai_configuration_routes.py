from fastapi import APIRouter, Depends

from app.models.ai_configuration_model import AIConfigurationInput, AIConfigurationResponse, ConnectionTestResponse
from app.services.ai.ai_configuration_service import activate_configuration, get_configuration, public_error, remove_configuration, validate_configuration
from app.services.ai.provider_catalog import public_provider_catalog
from app.utils.auth_dependency import get_current_user
from app.utils.project_authorization import require_project_admin, require_project_member

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["Project AI Configuration"])


@router.get("/providers")
async def list_providers(project_id: str, current_user=Depends(get_current_user)):
    await require_project_member(project_id, current_user)
    return public_provider_catalog()


@router.get("/configuration", response_model=AIConfigurationResponse | None)
async def read_configuration(project_id: str, current_user=Depends(get_current_user)):
    await require_project_member(project_id, current_user)
    return await get_configuration(project_id)


@router.post("/configuration/test", response_model=ConnectionTestResponse)
async def test_connection(project_id: str, payload: AIConfigurationInput, current_user=Depends(get_current_user)):
    await require_project_admin(project_id, current_user)
    try:
        await validate_configuration(project_id, payload)
        return {"success": True, "code": "CONNECTED"}
    except Exception as exc:
        raise public_error(exc) from None


@router.put("/configuration", response_model=AIConfigurationResponse)
async def save_and_activate(project_id: str, payload: AIConfigurationInput, current_user=Depends(get_current_user)):
    await require_project_admin(project_id, current_user)
    try:
        return await activate_configuration(project_id, payload, current_user["email"].strip().lower())
    except Exception as exc:
        raise public_error(exc) from None


@router.delete("/configuration")
async def delete_configuration(project_id: str, current_user=Depends(get_current_user)):
    await require_project_admin(project_id, current_user)
    await remove_configuration(project_id)
    return {"message": "AI configuration removed"}
