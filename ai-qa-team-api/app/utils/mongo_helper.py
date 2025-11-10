from bson import ObjectId

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if not doc:
        return None

    # Convert ObjectId to string and rename to 'id'
    doc["id"] = str(doc["_id"]) if "_id" in doc else None
    doc.pop("_id", None)
    return doc


def serialize_list(docs: list) -> list:
    """Serialize a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs]
