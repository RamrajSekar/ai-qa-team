from fastapi import Request, HTTPException, Depends
from app.db.connection import db
from app.utils.jwt_handler import decode_token
from app.utils.mongo_helper import serialize_doc
import jwt

# security = HTTPBearer()
# SECRET_KEY = settings.jwt_secret_key
# ALGORITHM = "HS256"

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Access token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid access token")

    email = payload.get("email")
    user = await db["users"].find_one({"email": email})

    if not user:
        raise HTTPException(404, "User not found")

    return serialize_doc(user)


def role_required(role: str):
    async def check_role(user=Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(403, "Not allowed")
        return user
    return check_role

