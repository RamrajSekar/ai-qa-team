from fastapi import APIRouter, HTTPException, Depends
from app.db.connection import db
from app.utils.auth_dependency import get_current_user

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

@router.get("/")
async def get_scenarios(current_user=Depends(get_current_user)):
    return {"message": f"Scenarios visible to {current_user['email']}"}