from app.config import settings
from app.db.connection import db

PLATFORM_OWNER = "OWNER"
PLATFORM_ADMIN = "ADMIN"
PLATFORM_NONE = "NONE"


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def platform_role(user: dict) -> str:
    value = user.get("platform_role", PLATFORM_NONE)
    return value if value in {PLATFORM_OWNER, PLATFORM_ADMIN} else PLATFORM_NONE


async def ensure_platform_owner(user: dict, *, trusted_for_bootstrap: bool, users_collection=None) -> dict:
    """Persist OWNER on a trusted match; never demote an existing role."""
    if platform_role(user) == PLATFORM_OWNER or not trusted_for_bootstrap:
        user["platform_role"] = platform_role(user)
        return user
    owner_email = normalize_email(settings.platform_owner_email)
    user_email = normalize_email(user.get("email"))
    if owner_email and user_email == owner_email:
        query = {"_id": user["_id"]} if user.get("_id") is not None else {"email": user.get("email")}
        collection = users_collection if users_collection is not None else db["users"]
        await collection.update_one(query, {"$set": {"platform_role": PLATFORM_OWNER}})
        user["platform_role"] = PLATFORM_OWNER
    else:
        user["platform_role"] = platform_role(user)
    return user
