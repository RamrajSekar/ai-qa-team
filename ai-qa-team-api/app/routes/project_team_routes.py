from fastapi import APIRouter, Depends

from app.models.project_membership_model import (
    ProjectInvitationCreate,
    ProjectMembershipResponse,
    ProjectMembershipUpdate,
    ProjectTeamResponse,
)
from app.services.project_team_service import change_member_role, invite_member, list_team, remove_member
from app.utils.auth_dependency import get_current_user


router = APIRouter(prefix="/projects/{project_id}/team", tags=["Project Team"])


@router.get("", response_model=ProjectTeamResponse)
async def get_project_team(project_id: str, current_user=Depends(get_current_user)):
    return await list_team(project_id, current_user)


@router.post("", response_model=ProjectMembershipResponse)
async def invite_project_member(project_id: str, request: ProjectInvitationCreate, current_user=Depends(get_current_user)):
    return await invite_member(project_id, request.email, request.role, current_user)


@router.patch("/{membership_id}", response_model=ProjectMembershipResponse)
async def update_project_member(project_id: str, membership_id: str, request: ProjectMembershipUpdate, current_user=Depends(get_current_user)):
    return await change_member_role(project_id, membership_id, request.role, current_user)


@router.delete("/{membership_id}")
async def delete_project_member(project_id: str, membership_id: str, current_user=Depends(get_current_user)):
    await remove_member(project_id, membership_id, current_user)
    return {"message": "Project member removed"}
