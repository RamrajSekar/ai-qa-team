from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr


ProjectRole = Literal["ADMIN", "TESTER"]
MembershipStatus = Literal["INVITED", "ACTIVE"]


class ProjectInvitationCreate(BaseModel):
    email: EmailStr
    role: ProjectRole


class ProjectMembershipUpdate(BaseModel):
    role: ProjectRole


class ProjectMembershipResponse(BaseModel):
    membership_id: str
    project_id: str
    user_id: str | None = None
    email: EmailStr
    name: str | None = None
    role: ProjectRole
    status: MembershipStatus
    invited_by: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectTeamResponse(BaseModel):
    current_user_role: ProjectRole
    members: list[ProjectMembershipResponse]
