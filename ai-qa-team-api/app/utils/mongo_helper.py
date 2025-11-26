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
