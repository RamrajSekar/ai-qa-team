from fastapi import Depends, HTTPException

from app.services.platform_role_service import PLATFORM_ADMIN, PLATFORM_OWNER, platform_role
from app.utils.auth_dependency import get_current_user


async def require_platform_admin(current_user=Depends(get_current_user)) -> dict:
    if platform_role(current_user) not in {PLATFORM_OWNER, PLATFORM_ADMIN}:
        raise HTTPException(403, "Platform administrator access required")
    return current_user


async def require_platform_owner(current_user=Depends(get_current_user)) -> dict:
    if platform_role(current_user) != PLATFORM_OWNER:
        raise HTTPException(403, "Platform owner access required")
    return current_user
