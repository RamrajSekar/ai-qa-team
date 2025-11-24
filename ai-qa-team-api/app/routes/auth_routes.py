from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.db.connection import db
from app.models.user_model import User
from app.config import settings
from app.utils.redis_client import store_refresh_token, get_refresh_token, delete_refresh_token
from app.utils.auth_dependency import get_current_user
from passlib.context import CryptContext
from app.utils.oauth_client import oauth
from pydantic import BaseModel, Field
from app.utils.mongo_helper import serialize_doc, serialize_list
import jwt
import json
from app.utils.auth_dependency import get_current_user, role_required
from app.utils.jwt_handler import create_access_token, decode_token, create_refresh_token
from datetime import datetime
import urllib.parse


router = APIRouter(prefix="/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

@router.post("/signup")
async def signup(user: User):
    existing = await db["users"].find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = pwd_context.hash(user.password)
    user.password = hashed_pw
    await db["users"].insert_one(user.model_dump(exclude={"id"}))
    return {"message": "Signup successful"}

@router.post("/login")
async def login(credentials: dict):
    user = await db["users"].find_one({"email": credentials["email"]})
    if not user or not pwd_context.verify(credentials["password"], user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"email": user["email"], "role": user["role"]})
    refresh_token = create_refresh_token({"email": user["email"]})
    store_refresh_token(user["email"], refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/{provider}/login")
async def oauth_login(request: Request, provider: str):
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(status_code=404, detail="Unsupported provider")

    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)
    # return await client.authorize_redirect(request, settings.re)


# @router.get("/{provider}/callback", name="oauth_callback")
# async def oauth_callback(request: Request, provider: str):
#     try:
#         client = oauth.create_client(provider)
#         if client is None:
#             raise HTTPException(status_code=404, detail="Unsupported provider")

#         token = await client.authorize_access_token(request)
        
#         if provider == "google":
#             user_info = token["userinfo"]
#         elif provider == "github":
#             user_info = await client.get("user", token=token)
#             user_info = user_info.json()
#         else:
#             raise HTTPException(status_code=400, detail="Unsupported provider response")

#         # Normalize user data
#         email = user_info.get("email")
#         name = user_info.get("name") or user_info.get("login")

#         existing = await db["users"].find_one({"email": email})
#         if not existing:
#             new_user = User(_id=user_info.get("id"), name=name, email=email, provider=provider, role="tester")
#             await db["users"].insert_one(new_user.model_dump(by_alias=True, exclude_none=True))

#         # ✅ Generate tokens
#         access_token = create_access_token({"email": email, "role": "tester"})
#         refresh_token = create_refresh_token({"email": email, "role": "tester"})

#         # ✅ Store refresh token in Redis (optional)
#         store_refresh_token(email, refresh_token)
#         return {
#                 "access_token": access_token,
#                 "refresh_token": refresh_token,
#                 "token_type": "bearer",
#                 "user": {
#                     "name": name,
#                     "email": email,
#                     "provider": provider,
#                     "role": "tester"
#                 }
#             }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@router.get("/{provider}/callback", name="oauth_callback")
async def oauth_callback(request: Request, provider: str):
    """
    OAuth callback:
    - Called by Google/GitHub after user grants access
    - Creates user (if new), issues access + refresh tokens
    - REDIRECTS back to frontend with tokens in URL query
    """

    try:
        client = oauth.create_client(provider)
        if client is None:
            raise HTTPException(status_code=404, detail="Unsupported provider")

        token = await client.authorize_access_token(request)

        # ---- normalize user info from provider ----
        if provider == "google":
            user_info = token["userinfo"]
        elif provider == "github":
            user_info = await client.get("user", token=token)
            user_info = user_info.json()
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider response")

        email = user_info.get("email")
        name = user_info.get("name") or user_info.get("login")

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by provider")

        # ---- upsert user ----
        existing = await db["users"].find_one({"email": email})
        if not existing:
            new_user = User(
                _id=user_info.get("id"),
                name=name,
                email=email,
                provider=provider,
                role="tester",
            )
            await db["users"].insert_one(
                new_user.model_dump(by_alias=True, exclude_none=True)
            )

        # ---- issue tokens ----
        access_token = create_access_token({"email": email, "role": "tester"})
        refresh_token = create_refresh_token({"email": email, "role": "tester"})

        # store refresh token in Redis
        store_refresh_token(email, refresh_token)

        # ---- REDIRECT BACK TO FRONTEND ----
        # FRONTEND_URL should be like: http://localhost:3000
        frontend_base = settings.frontend_url.rstrip("/") if hasattr(settings, "frontend_url") else "http://localhost:3000"

        # We’ll handle this URL in Next.js at /auth/callback
        params = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "provider": provider,
            "user": {
                "name": name,
                "email": email,
                "provider": provider,
                "role": "tester"
            }
        }
        # Convert to JSON string
        payload = json.dumps(params)
        query = urllib.parse.urlencode({"data": payload})
        redirect_url = f"{frontend_base}/oauth/callback?{query}"
        response = RedirectResponse(url=redirect_url)

        print("STEP 1: Entered OAuth callback")
        print("Provider:", provider)
        print("User info received from provider:", user_info)

        print("STEP 2: Issued tokens:")
        print("Access token:", access_token)
        print("Refresh token:", refresh_token)

        print("STEP 3: Redirecting user to:", redirect_url)

        # Set secure httpOnly cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=86400,
            secure=False,  # set True on production (HTTPS)
            samesite="lax",
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=604800,
            secure=False,  # True in prod
            samesite="lax",
            path="/"
        )
        print("STEP 4: Cookies set on response:")
        print("All response cookies:", response.headers.getlist("set-cookie"))

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@router.post("/refresh")
async def refresh_token(data: dict):
    old_token = data.get("refresh_token")
    if not old_token:
        raise HTTPException(status_code=400, detail="Missing refresh token")

    try:
        payload = decode_token(old_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")

        email = payload.get("email")
        stored_token = get_refresh_token(email)
        if stored_token != old_token:
            raise HTTPException(status_code=401, detail="Refresh token expired or invalidated")

        # Issue new access token
        new_access = create_access_token({"email": email, "role": payload.get("role", "tester")})
        return {"access_token": new_access, "token_type": "bearer"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.patch("/update-role")
async def update_user_role(
    data: dict,
    current_user=Depends(role_required("admin"))
):
    """
    Allows only Admins to promote or demote users.
    Expects JSON like:
    {
      "email": "tester@example.com",
      "new_role": "lead"
    }
    """
    email = data.get("email")
    new_role = data.get("new_role")

    if not email or not new_role:
        raise HTTPException(status_code=400, detail="Email and new_role are required")

    if new_role not in ["tester", "lead", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role value")

    # Update the role in MongoDB
    result = await db["users"].update_one(
        {"email": email},
        {"$set": {"role": new_role}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or role unchanged")

    return {
        "message": f"User {email} promoted to {new_role}",
        "updated_by": current_user["email"]
    }

# @router.get("/me")
# async def get_my_profile(current_user=Depends(get_current_user)):
#     user_email = current_user.get("email")
#     user = await db["users"].find_one({"email": user_email})

#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     user_data = serialize_doc(user)
#     user_data["token_issued_to"] = user_email
#     user_data["token_checked_at"] = datetime.utcnow().isoformat()

#     return user_data

@router.get("/me")
async def get_my_profile(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token")

    user_email = payload.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    user = await db["users"].find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = serialize_doc(user)
    user_data["token_issued_to"] = user_email
    user_data["token_checked_at"] = datetime.utcnow().isoformat()
    print("STEP 5: /auth/me called")
    print("Received cookies:", request.cookies)
    print("Decoded user:", user_data)
    return user_data

@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    delete_refresh_token(current_user["email"])
    return {"message": "Logged out successfully"}