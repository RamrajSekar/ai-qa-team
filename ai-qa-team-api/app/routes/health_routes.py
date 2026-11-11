from fastapi import APIRouter
from app.db.connection import db

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    try:
        # Try running a lightweight DB command
        await db.command("ping")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": f"failed: {str(e)}"}
