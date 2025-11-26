from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.db.connection import db
from app.models.user_model import User
from app.models.subscription import Subscription
from app.services.subscription_services import get_subscription
from app.utils.jwt_handler import create_access_token, create_refresh_token
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
# -----------------------------
# Request Models
# -----------------------------

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# -----------------------------
# SIGNUP
# -----------------------------
@router.post("/signup")
async def signup(req: SignupRequest):

    existing = await db["users"].find_one({"email": req.email})
    if existing:
        raise HTTPException(400, "Email already exists")

    hashed_pw = pwd_context.hash(req.password)
    user = User(
        name=req.name,
        email=req.email,
        password=hashed_pw,
        provider="local",
        role="admin",  # default
        subscription=Subscription()
    )

    await db["users"].insert_one(user.model_dump(by_alias=True))

    # Create tokens
    access = create_access_token({"email": user.email, "role": user.role})
    refresh = create_refresh_token({"email": user.email, "role": user.role})
    hashed_access = pwd_context.hash(access)
    hashed_refresh = pwd_context.hash(refresh)
    return {
        "user": user.model_dump(),
        "access_token": access,
        "refresh_token": refresh,
    }


# -----------------------------
# LOGIN
# -----------------------------
@router.post("/login")
async def login(req: LoginRequest):

    user = await db["users"].find_one({"email": req.email})
    if not user:
        raise HTTPException(400, "Invalid credentials")

    if not verify_password(req.password, user.get("password", "")):
        raise HTTPException(400, "Invalid credentials")

    # Heal subscription if missing
    subscription = await get_subscription(req.email)

    access = create_access_token({"email": user["email"], "role": user["role"]})
    refresh = create_refresh_token({"email": user["email"], "role": user["role"]})
    hashed_access = pwd_context.hash(access)
    hashed_refresh = pwd_context.hash(refresh)
    print("LOGIN USER:", user)
    return {
        "user": user,
        "access_token": access,
        "refresh_token": refresh,
        "subscription": subscription
    }


# # -----------------------------
# # CURRENT USER
# # -----------------------------
# from app.utils.auth_dependency import get_current_user

# @router.get("/me")
# async def me(current_user = Depends(get_current_user)):
#     return current_user
