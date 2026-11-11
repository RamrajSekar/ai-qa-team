from uuid import uuid4

from app.db.connection import db
from fastapi import HTTPException
from app.models.environment_model import ProjectEnvironment, ProjectEnvironmentResponse
from app.services.story_service import get_next_sequence
from app.services.secrets.environment_secrets import encrypt_secrets, public_environment, read_secrets
from app.utils.project_authorization import require_project_admin, require_project_member


def prepare_document(env, env_id, existing=None):
    existing = existing or {}
    roles = [credential.role.strip().lower() for credential in env.credentials]
    if any(not role for role in roles) or len(roles) != len(set(roles)):
        raise HTTPException(422, "Credential roles must be nonempty and unique.")
    if env.revision is not None and env.revision != existing.get("revision", 0):
        raise HTTPException(409, "Environment changed. Reload before saving.")
    secrets = read_secrets(existing) if existing else {"passwords": {}, "auth_token": None}
    old_credentials = existing.get("credentials", [])
    credentials = []
    passwords = {}
    for incoming in env.credentials:
        previous = next((item for item in old_credentials
                         if (incoming.credential_id and item.get("credential_id") == incoming.credential_id)
                         or (not incoming.credential_id and item["role"].strip().lower() == incoming.role.strip().lower())), None)
        password = incoming.password
        if not password and previous:
            password = secrets["passwords"].get(previous["role"].strip().lower(), "")
            if password and incoming.username != previous.get("username"):
                raise HTTPException(422, "Re-enter the password when changing a credential username.")
        if incoming.credential_id and not previous:
            raise HTTPException(409, "Credential changed. Reload before saving.")
        role = incoming.role.strip()
        passwords[role.lower()] = password
        credentials.append({"role": role, "username": incoming.username,
                            "credential_id": (previous or {}).get("credential_id") or uuid4().hex,
                            "notes": incoming.notes, "password": "", "password_configured": bool(password)})
    token = None
    if env.auth_type != "none" and not env.clear_auth_token:
        token = env.auth_token
        if not token and env.auth_type == existing.get("auth_type"):
            token = secrets.get("auth_token")
    document = env.model_dump(exclude={"env_id", "credentials", "clear_auth_token"})
    document.update({"project_id": existing.get("project_id", env.project_id), "env_id": env_id,
                     "credentials": credentials, "auth_token": None, "auth_token_configured": bool(token),
                     "revision": existing.get("revision", 0) + 1})
    document["secret_payload"] = encrypt_secrets(document, passwords, token)
    return document


def revision_query(existing):
    return {"env_id": existing["env_id"], "project_id": existing["project_id"],
            "revision": existing["revision"] if "revision" in existing else {"$exists": False}}


async def create_environment(env: ProjectEnvironment, current_user):
    await require_project_admin(env.project_id, current_user)
    env_id = await get_next_sequence("env_id", "ENV")
    document = prepare_document(env, env_id)
    document["created_by"] = current_user["email"]
    result = await db["environments"].insert_one(document)
    document["_id"] = result.inserted_id
    await db["users"].update_one({"email": current_user["email"]}, {"$set": {
        "onboarding.context.environment_id": env_id, "onboarding.steps.environment": True,
        "onboarding.current_step": 3,
    }})
    return ProjectEnvironmentResponse(**public_environment(document))


async def list_environments(project_id: str | None, current_user):
    if project_id:
        await require_project_member(project_id, current_user)
        query = {"project_id": project_id}
    else:
        memberships = await db["project_memberships"].find({
            "email": current_user["email"].lower(), "status": "ACTIVE",
        }).to_list(500)
        query = {"project_id": {"$in": [item["project_id"] for item in memberships]}}
    documents = await db["environments"].find(query).to_list(100)
    return [public_environment(document) for document in documents]


async def get_environment(env_id: str, current_user):
    document = await db["environments"].find_one({"env_id": env_id})
    if not document:
        raise HTTPException(404, "Environment not found")
    await require_project_member(document["project_id"], current_user)
    return ProjectEnvironmentResponse(**public_environment(document))


async def update_environment(env_id: str, env: ProjectEnvironment, current_user):
    existing = await db["environments"].find_one({"env_id": env_id})
    if not existing:
        raise HTTPException(404, "Environment not found")
    await require_project_admin(existing["project_id"], current_user)
    if env.project_id != existing["project_id"]:
        raise HTTPException(409, "An environment cannot be moved to another project.")
    document = prepare_document(env, env_id, existing)
    result = await db["environments"].update_one(revision_query(existing), {"$set": document})
    if result.matched_count == 0:
        raise HTTPException(409, "Environment changed. Reload before saving.")
    return ProjectEnvironmentResponse(**public_environment({**existing, **document}))


async def delete_environment(env_id: str, current_user):
    existing = await db["environments"].find_one({"env_id": env_id})
    if not existing:
        raise HTTPException(404, "Environment not found")
    await require_project_admin(existing["project_id"], current_user)
    deleted = await db["environments"].delete_one(revision_query(existing))
    if deleted.deleted_count == 0:
        raise HTTPException(409, "Environment changed. Reload before deleting.")
    return {"message": "Environment deleted"}


async def resolve_environment_credentials(project_id, env_id, role, current_user):
    """Trusted runtime only. Never return this result from an API or persist it in a job."""
    await require_project_member(project_id, current_user)
    document = await db["environments"].find_one({"project_id": project_id, "env_id": env_id})
    if not document:
        raise HTTPException(404, "Environment not found")
    credential = next((item for item in document.get("credentials", [])
                       if item["role"].strip().lower() == role.strip().lower()), None)
    if not credential:
        raise HTTPException(404, "Application role not found")
    secrets = read_secrets(document)
    return {"username": credential["username"],
            "password": secrets["passwords"].get(credential["role"].strip().lower(), ""),
            "auth_token": secrets.get("auth_token"), "revision": document.get("revision", 0)}
