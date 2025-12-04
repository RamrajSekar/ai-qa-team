from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.utils.auth_dependency import get_current_user
from app.models.environment_model import (
    ProjectEnvironment,
    ProjectEnvironmentResponse,
)
from app.services.project_environment_service import (
    create_environment,
    list_environments,
    get_environment,
    update_environment,
    delete_environment,
)

router = APIRouter(prefix="/environments", tags=["Environments"])

# -------------------------------------------------------
# CREATE ENVIRONMENT
# -------------------------------------------------------
@router.post(
    "",
    response_model=ProjectEnvironmentResponse,
    summary="Create Environment",
    description="Create a new environment for a project",
)
async def create_env(
    env: ProjectEnvironment,
    current_user=Depends(get_current_user)
):
    return await create_environment(env, current_user)

# -------------------------------------------------------
# LIST ENVIRONMENTS
# -------------------------------------------------------
@router.get(
    "",
    response_model=list[ProjectEnvironmentResponse],
    summary="List Environments",
)
@router.get(
    "/",
    response_model=list[ProjectEnvironmentResponse],
    summary="List Environments",
)
async def get_envs(
    project_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    return await list_environments(project_id, current_user)

# -------------------------------------------------------
# GET SINGLE ENVIRONMENT
# -------------------------------------------------------
@router.get(
    "/{env_id}",
    response_model=ProjectEnvironmentResponse,
    summary="Get Environment by ID",
)
async def get_env(
    env_id: str,
    current_user=Depends(get_current_user)
):
    return await get_environment(env_id, current_user)

# -------------------------------------------------------
# UPDATE ENVIRONMENT
# -------------------------------------------------------
@router.patch(
    "/{env_id}",
    response_model=ProjectEnvironmentResponse,
    summary="Update Environment",
)
async def patch_env(
    env_id: str,
    env: ProjectEnvironment,
    current_user=Depends(get_current_user)
):
    return await update_environment(env_id, env, current_user)

# -------------------------------------------------------
# DELETE ENVIRONMENT
# -------------------------------------------------------
@router.delete(
    "/{env_id}",
    summary="Delete Environment",
)
async def delete_env(
    env_id: str,
    current_user=Depends(get_current_user)
):
    return await delete_environment(env_id, current_user)
