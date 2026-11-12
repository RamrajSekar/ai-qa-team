from fastapi import APIRouter, Depends

from app.models.prompt_registry_model import PromptDraftCreate, PromptDraftUpdate
from app.services.prompt_registry_service import activate_version, create_draft, get_prompt_definition, list_prompts, list_versions, update_draft
from app.utils.safe_validation_route import SafeValidationRoute
from app.utils.platform_authorization import require_platform_admin

router = APIRouter(prefix="/platform-admin", tags=["Platform Administration"], route_class=SafeValidationRoute)


@router.get("")
async def platform_admin_dashboard(current_user=Depends(require_platform_admin)):
    return {"available_modules": ["PROMPT_MANAGEMENT"]}


@router.get("/prompts")
async def get_prompts(current_user=Depends(require_platform_admin)):
    return await list_prompts()


@router.get("/prompts/{prompt_key}")
async def get_prompt(prompt_key: str, current_user=Depends(require_platform_admin)):
    return await get_prompt_definition(prompt_key)


@router.get("/prompts/{prompt_key}/versions")
async def get_prompt_versions(prompt_key: str, current_user=Depends(require_platform_admin)):
    return await list_versions(prompt_key)


@router.post("/prompts/{prompt_key}/versions")
async def post_prompt_version(prompt_key: str, payload: PromptDraftCreate, current_user=Depends(require_platform_admin)):
    return await create_draft(prompt_key, current_user["email"], payload.base_version)


@router.patch("/prompts/{prompt_key}/versions/{version}")
async def patch_prompt_version(prompt_key: str, version: int, payload: PromptDraftUpdate, current_user=Depends(require_platform_admin)):
    return await update_draft(prompt_key, version, payload.system_prompt)


@router.post("/prompts/{prompt_key}/versions/{version}/activate")
async def post_activate_prompt_version(prompt_key: str, version: int, current_user=Depends(require_platform_admin)):
    return await activate_version(prompt_key, version)
