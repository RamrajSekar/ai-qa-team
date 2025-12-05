from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse,JSONResponse
from authlib.integrations.starlette_client import OAuth
from app.db.connection import db
from app.models.user_model import User, OnboardingModel
from app.config import settings
from app.utils.redis_client import store_refresh_token, get_refresh_token, delete_refresh_token
from passlib.context import CryptContext
from app.utils.oauth_client import oauth
from pydantic import BaseModel, Field
from app.utils.mongo_helper import serialize_doc, serialize_list
import jwt
import json
from app.utils.auth_dependency import get_current_user, role_required, extract_token
from app.utils.jwt_handler import create_access_token, decode_token, create_refresh_token
from datetime import datetime, timezone
import urllib.parse
from app.models.subscription import Subscription

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



def to_json_safe(obj):
    if isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_json_safe(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

@router.post("/signup")
async def signup(user: User):
    try:
        # 1️⃣ Check for existing email BEFORE doing anything else
        existing = await db["users"].find_one({"email": user.email})
        if existing:
            raise HTTPException(400, "Email already exists")

        # 2️⃣ Hash password
        hashed_pw = pwd_context.hash(user.password)

        # 3️⃣ Create subscription (in memory)
        subscription = Subscription(plan="free")
        subscription.apply_plan_defaults()
        subscription_dict = subscription.model_dump()

        onboarding = OnboardingModel()
        # 4️⃣ Prepare user document (NOT Pydantic model)
        user_doc = {
            "name": user.name,
            "email": user.email,
            "password": hashed_pw,
            "provider": "local",
            "role": "admin",
            "subscription": subscription_dict,
            "onboarding":onboarding.model_dump(),
            "created_at": datetime.now(timezone.utc),
        }

        # 5️⃣ Insert ONLY AFTER everything validated
        result = await db["users"].insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)

        # 6️⃣ Generate tokens
        access = create_access_token({"email": user.email, "role": "admin"})
        refresh = create_refresh_token({"email": user.email, "role": "admin"})
        safe_user_doc = to_json_safe(user_doc)
        response = JSONResponse({"user": safe_user_doc})
        response.set_cookie("access_token", access, httponly=True, samesite="lax")
        response.set_cookie("refresh_token", refresh, httponly=True, samesite="lax")
        return response
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@router.post("/login")
async def login(credentials: dict):
    print("LOGIN REQ =", credentials["email"], credentials["password"])
    user = await db["users"].find_one({"email": credentials["email"]})
    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not pwd_context.verify(credentials["password"], user["password"]):
        raise HTTPException(401, "Invalid credentials")

    user_data = serialize_doc(user)

    access = create_access_token({"email": user_data["email"], "role": user_data["role"]})
    refresh = create_refresh_token({"email": user_data["email"], "role": user_data["role"]})

    store_refresh_token(user_data["email"], refresh)

    # --- FIX: Set cookies ---
    response = JSONResponse({
        "user": user_data,
        "status": "ok"
    })

    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=False, # true in production
        samesite="lax",
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=False, # true in production
        samesite="lax",
        path="/",
    )

    return response

@router.get("/{provider}/login")
async def oauth_login(request: Request, provider: str, callback: str | None = None):
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(404, "Unsupported provider")

    # Allow frontend override
    redirect_uri = request.url_for("oauth_callback", provider=provider)

    if callback:
        redirect_uri = callback
    return await client.authorize_redirect(request, redirect_uri)


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

        # ---- UPSERT USER ----
        existing = await db["users"].find_one({"email": email})

        if not existing:
            # brand new user
            new_user = User(
                _id=user_info.get("id"),
                name=name,
                email=email,
                provider=provider,
                role="tester",
            )

            user_doc = new_user.model_dump(by_alias=True, exclude_none=True)

            # 🔥 Save test import access token
            user_doc["integrations"] = {
                provider: {
                    "access_token": token.get("access_token"),
                    "token_type": token.get("token_type"),
                    "scope": token.get("scope"),
                    "raw": token,
                }
            }

            await db["users"].insert_one(user_doc)

        else:
            # existing user → update integrations
            await db["users"].update_one(
                {"email": email},
                {
                    "$set": {
                        "provider": provider,
                        f"integrations.{provider}.access_token": token.get("access_token"),
                        f"integrations.{provider}.token_type": token.get("token_type"),
                        f"integrations.{provider}.scope": token.get("scope"),
                        f"integrations.{provider}.raw": token,
                    }
                }
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
        # print("User info received from provider:", user_info)

        print("STEP 2: Issued tokens:")
        # print("Access token:", access_token)
        # print("Refresh token:", refresh_token)

        print("STEP 3: Redirecting user")

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
        # print("All response cookies:", response.headers.getlist("set-cookie"))

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@router.post("/refresh")
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh token")

    try:
        payload = decode_token(refresh_token)
        email = payload.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored = get_refresh_token(email)
    if stored != refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    # Issue NEW access token
    new_access = create_access_token({"email": email, "role": payload.get("role")})
    response = JSONResponse({"access_token": new_access})
    response.set_cookie("access_token", new_access, httponly=True)

    return response


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

@router.get("/me")
async def get_my_profile(request: Request):
    token = extract_token(request)
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
    # print("Received cookies:", request.cookies)
    user_data.pop("password", None)
    print("Decoded user:", user_data)
    return { "ok": True, "user": user_data }

# @router.post("/logout")
# async def logout(current_user=Depends(get_current_user)):
#     delete_refresh_token(current_user["email"])
    return {"message": "Logged out successfully"}

@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    # 1️⃣ Invalidate refresh token in Redis
    delete_refresh_token(current_user["email"])

    # 2️⃣ Build response
    response = JSONResponse({"message": "Logged out successfully"})

    # 3️⃣ Clear cookies (must match original cookie attributes)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=False,  # TRUE in production HTTPS
        samesite="lax",
        path="/"
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=False,  # TRUE in production
        samesite="lax",
        path="/"
    )

    return response