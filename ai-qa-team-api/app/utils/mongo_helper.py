from bson import ObjectId
from datetime import datetime

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    result = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = serialize_doc(v)
        else:
            result[k] = v
    return result


def serialize_list(docs: list) -> list:
    """Serialize a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs]


_PUBLIC_USER_FIELDS = {
    "_id",
    "id",
    "name",
    "email",
    "provider",
    "role",
    "platform_role",
    "account_id",
    "account_role",
    "account_state",
    "onboarding",
    "subscription",
    "created_at",
    "updated_at",
}


def serialize_public_user(doc: dict) -> dict:
    """Serialize only fields that are safe to return in public user payloads."""
    result = serialize_doc({key: value for key, value in doc.items() if key in _PUBLIC_USER_FIELDS})
    result["platform_role"] = doc.get("platform_role", "NONE")
    return result
