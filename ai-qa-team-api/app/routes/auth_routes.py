from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse,JSONResponse
from app.db.connection import db
from app.models.user_model import User, OnboardingModel
from app.config import settings
from app.utils.redis_client import store_refresh_token, get_refresh_token, delete_refresh_token
from passlib.context import CryptContext
from app.utils.oauth_client import oauth
from app.utils.mongo_helper import serialize_public_user
from app.utils.auth_cookies import clear_auth_cookies, set_access_cookie, set_auth_cookies
import jwt
from app.utils.auth_dependency import get_current_user, role_required, extract_token
from app.utils.jwt_handler import create_access_token, decode_token, create_refresh_token
from datetime import datetime, timezone
from app.models.subscription import Subscription
from app.services.sync_usage import sync_usage
from app.services.project_team_service import activate_pending_memberships
from app.services.platform_role_service import ensure_platform_owner
from app.services.customer_accounts import CustomerAccounts, enabled as accounts_enabled
from app.utils.safe_validation_route import SafeValidationRoute


router = APIRouter(prefix="/auth", tags=["Auth"], route_class=SafeValidationRoute)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def google_identity_metadata(user_info: dict) -> dict:
    """Return the non-secret Google identity fields retained by the application."""
    metadata = {
        "provider": "google",
        "provider_user_id": user_info.get("sub") or user_info.get("id"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "updated_at": datetime.now(timezone.utc),
    }
    return {key: value for key, value in metadata.items() if value is not None}


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
        normalized_email = str(user.email).strip().lower()
        existing = await db["users"].find_one({"email": normalized_email})
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
            "email": normalized_email,
            "password": hashed_pw,
            "provider": "local",
            "role": "admin",
            "platform_role": "NONE",
            "subscription": subscription_dict,
            "onboarding":onboarding.model_dump(),
            "created_at": datetime.now(timezone.utc),
        }

        # 5️⃣ Insert ONLY AFTER everything validated
        if accounts_enabled():
            await CustomerAccounts(db).register(user_doc, user.invitation_token.get_secret_value() if user.invitation_token else None)
        else:
            result = await db["users"].insert_one(user_doc)
            user_doc["_id"] = str(result.inserted_id)
        await ensure_platform_owner(user_doc, trusted_for_bootstrap=True, users_collection=db["users"])

        # 6️⃣ Generate tokens
        access = create_access_token({"email": normalized_email, "role": "admin"})
        refresh = create_refresh_token({"email": normalized_email, "role": "admin"})
        store_refresh_token(normalized_email, refresh)
        safe_user_doc = serialize_public_user(user_doc)
        response = JSONResponse({"user": safe_user_doc})
        set_auth_cookies(response, access, refresh)
        return response
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Signup could not be completed. Contact support before retrying a partially created account.") from None


@router.post("/login")
async def login(credentials: dict):
    # print("LOGIN REQ =", credentials["email"], credentials["password"])
    user = await db["users"].find_one({"email": str(credentials["email"]).strip().lower()})
    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not pwd_context.verify(credentials["password"], user["password"]):
        raise HTTPException(401, "Invalid credentials")

    if accounts_enabled() or user.get("account_id"):
        await CustomerAccounts(db).require(user)
    await ensure_platform_owner(user, trusted_for_bootstrap=True, users_collection=db["users"])
    user_data = serialize_public_user(user)
    if user.get("account_id"):
        from app.services.account_billing import billing_account
        account = await billing_account(db, user)
        if account:
            user_data["subscription"] = to_json_safe(account["subscription"])
            user_data["billing_scope"] = "ACCOUNT"

    access = create_access_token({"email": user_data["email"], "role": user_data["role"]})
    refresh = create_refresh_token({"email": user_data["email"], "role": user_data["role"]})

    store_refresh_token(user_data["email"], refresh)

    # --- FIX: Set cookies ---
    response = JSONResponse({
        "user": user_data,
        "status": "ok"
    })

    set_auth_cookies(response, access, refresh)

    return response

@router.get("/{provider}/login")
async def oauth_login(request: Request, provider: str):
    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(404, "Unsupported provider")

    redirect_uri = getattr(settings, f"{provider}_redirect_uri", None)
    if not redirect_uri:
        raise HTTPException(500, f"{provider.upper()}_REDIRECT_URI is not configured")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback", name="oauth_callback")
async def oauth_callback(request: Request, provider: str):
    """
    OAuth callback:
    - Called by Google/GitHub after user grants access
    - Creates user (if new), issues access + refresh tokens
    - Sets server-side auth cookies and redirects to the frontend dashboard
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

        if accounts_enabled() and provider == "github":
            email_response = await client.get("user/emails", token=token)
            verified = next((item for item in email_response.json() if item.get("primary") and item.get("verified")), None)
            if not verified:
                raise HTTPException(400, "A verified primary provider email is required.")
            user_info["email"] = verified["email"]
            user_info["email_verified"] = True
        if accounts_enabled() and user_info.get("email_verified") is not True:
            raise HTTPException(400, "A verified provider email is required.")
        email = str(user_info.get("email") or "").strip().lower()
        name = user_info.get("name") or user_info.get("login")

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by provider")

        # ---- UPSERT USER ----
        existing = await db["users"].find_one({"email": email})
        if provider == "google":
            integration_data = google_identity_metadata(user_info)
        else:
            # Repository-provider credentials remain outside this Google-only
            # remediation and are still required by the legacy import flow.
            integration_data = {
                "access_token": token.get("access_token"),
                "token_type": token.get("token_type"),
                "scope": token.get("scope"),
                "raw": token,
            }

        if not existing:
            # brand new user
            new_user = User(
                _id=str(user_info["id"]) if user_info.get("id") is not None else None,
                name=name,
                email=email,
                provider=provider,
                role="tester",
            )

            user_doc = new_user.model_dump(by_alias=True, exclude_none=True)

            # 🔥 ADD SUBSCRIPTION + LIMITS
            subscription = Subscription(plan="free")
            subscription.apply_plan_defaults()
            user_doc["subscription"] = subscription.model_dump()

            # 🔥 ADD ONBOARDING STRUCTURE
            user_doc["onboarding"] = OnboardingModel().model_dump()

            # 🔥 ADD REQUIRED METADATA
            user_doc["created_at"] = datetime.utcnow()

            user_doc["integrations"] = {provider: integration_data}

            if accounts_enabled():
                await CustomerAccounts(db).register(user_doc, verified_email=True)
            else:
                await db["users"].insert_one(user_doc)
            persisted_role = user_doc["role"]

        else:
            if accounts_enabled() or existing.get("account_id"):
                if user_info.get("email_verified") is not True:
                    raise HTTPException(400, "A verified provider email is required.")
                await CustomerAccounts(db).require(existing)
            # existing user → update integrations
            await db["users"].update_one(
                {"email": email},
                {
                    "$set": {
                        "provider": provider,
                        # Replacing the complete Google integration object also
                        # removes legacy raw/access/refresh/ID token fields.
                        f"integrations.{provider}": integration_data,
                        # 🔥 Ensure subscription exists (self-heal)
                        "subscription": existing.get("subscription") or Subscription(plan="free").model_dump(),
                        "onboarding": existing.get("onboarding") or OnboardingModel().model_dump(),
                    }
                }
            )
            persisted_role = existing.get("role", "tester")

        persisted_user = await db["users"].find_one({"email": email})
        if persisted_user:
            await ensure_platform_owner(
                persisted_user,
                trusted_for_bootstrap=provider == "google" and user_info.get("email_verified") is True,
                users_collection=db["users"],
            )
        if persisted_user and provider == "google" and user_info.get("email_verified") is True:
            await activate_pending_memberships(persisted_user)

        # ---- issue tokens using the persisted application role ----
        access_token = create_access_token({"email": email, "role": persisted_role})
        refresh_token = create_refresh_token({"email": email, "role": persisted_role})

        # store refresh token in Redis
        store_refresh_token(email, refresh_token)

        if not settings.frontend_url:
            raise HTTPException(status_code=500, detail="FRONTEND_URL is not configured")
        frontend_base = settings.frontend_url.rstrip("/")
        redirect_url = f"{frontend_base}/dashboard"
        response = RedirectResponse(url=redirect_url)
        set_auth_cookies(response, access_token, refresh_token)

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="OAuth sign-in could not be completed.") from None

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

    user = await db["users"].find_one({"email": email})
    if accounts_enabled() or (user and user.get("account_id")):
        if not user:
            raise HTTPException(401, "User not found.")
        await CustomerAccounts(db).require(user)
    # Issue NEW access token
    new_access = create_access_token({"email": email, "role": payload.get("role")})
    response = JSONResponse({"status": "ok"})
    set_access_cookie(response, new_access)

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

    account_scope = {}
    if accounts_enabled() or current_user.get("account_id"):
        account = await CustomerAccounts(db).admin(current_user)
        account_scope["account_id"] = account["_id"]
    # Update the role in MongoDB
    result = await db["users"].update_one(
        {"email": email, **account_scope},
        {"$set": {"role": new_role}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or role unchanged")

    return {
        "message": f"User {email} promoted to {new_role}",
        "updated_by": current_user["email"]
    }

@router.get("/me")
async def get_my_profile(request: Request, refresh_usage: bool = True):
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

    if accounts_enabled() or user.get("account_id"):
        await CustomerAccounts(db).require(user)
    if refresh_usage:
        await sync_usage(user_email)
        user = await db["users"].find_one({"email": user_email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    await ensure_platform_owner(
        user,
        trusted_for_bootstrap=user.get("provider", "local") == "local",
        users_collection=db["users"],
    )
    user_data = serialize_public_user(user)

    user_data["token_issued_to"] = user_email
    if user.get("account_id"):
        from app.services.account_billing import billing_account
        account = await billing_account(db, user)
        if account:
            user_data["subscription"] = to_json_safe(account["subscription"])
            user_data["billing_scope"] = "ACCOUNT"
    user_data["token_checked_at"] = datetime.utcnow().isoformat()

    return {"ok": True, "user": user_data}


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

    # 3️⃣ Clear cookies with the same shared attributes used when setting them
    clear_auth_cookies(response)

    return response
