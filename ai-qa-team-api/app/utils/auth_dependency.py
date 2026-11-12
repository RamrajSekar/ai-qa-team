from fastapi import Request, HTTPException, Depends
from app.db.connection import db
from app.utils.jwt_handler import decode_token
from app.utils.mongo_helper import serialize_doc
import jwt
from app.services.customer_accounts import CustomerAccounts, enabled as accounts_enabled

# security = HTTPBearer()
# SECRET_KEY = settings.jwt_secret_key
# ALGORITHM = "HS256"

def extract_token(request: Request):
    token = request.cookies.get("access_token")
    
    if not token:
        auth = request.headers.get("authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ")[1]
    
    return token


async def get_current_user(request: Request):
    token = extract_token(request)
    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid")

    email = payload.get("email")
    user = await db["users"].find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")

    if accounts_enabled() or user.get("account_id"):
        await CustomerAccounts(db).require(user)
        from app.utils.account_references import authorize_references
        await authorize_references(request, user, db)
    return serialize_doc(user)



def role_required(role: str):
    async def check_role(user=Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(403, "Not allowed")
        return user
    return check_role

