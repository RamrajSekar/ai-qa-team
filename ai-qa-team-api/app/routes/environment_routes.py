from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.auth_dependency import get_current_user
from app.db.connection import db
from app.models.environment_model import (
    ProjectEnvironment,
    ProjectEnvironmentResponse
)
from app.services.project_environment_service import (
    create_environment,
    list_environments,
    get_environment,
    update_environment,
    delete_environment
)
from typing import Optional


router = APIRouter(prefix="/environments", tags=["Environments"])


@router.post(
    "/",
    response_model=ProjectEnvironmentResponse,
    summary="Create Environment",
    description="Create a new environment tied to a project."
)
async def create_env(
    env: ProjectEnvironment,
    current_user=Depends(get_current_user)
):
    return await create_environment(env, current_user)


@router.get(
    "/",
    response_model=list[ProjectEnvironmentResponse],
    summary="List Environments",
    description="List all environments for the logged-in user."
)
async def get_envs(
    project_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user)
):
    return await list_environments(project_id, current_user)


@router.get(
    "/{env_id}",
    response_model=ProjectEnvironmentResponse,
    summary="Get Environment by ID"
)
async def get_env(
    env_id: str,
    current_user=Depends(get_current_user)
):
    return await get_environment(env_id, current_user)


@router.put(
    "/{env_id}",
    response_model=ProjectEnvironmentResponse,
    summary="Update Environment"
)
async def update_env(
    env_id: str,
    env: ProjectEnvironment,
    current_user=Depends(get_current_user)
):
    return await update_environment(env_id, env, current_user)


@router.delete(
    "/{env_id}",
    summary="Delete Environment"
)
async def delete_env(
    env_id: str,
    current_user=Depends(get_current_user)
):
    return await delete_environment(env_id, current_user)
