from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.db.connection import db
from app.models.repository_model import (
    DiscoveredTestResponse,
    RepositoryConnectRequest,
    RepositoryResponse,
)
from app.services.repository_discovery_service import (
    REPOSITORY_SCANNER_VERSION,
    static_scan,
    validate_branch,
    validate_local_repository_path,
    validate_public_github_url,
)
from app.services.test_registry_service import (
    REGISTRY_VERSION,
    build_test_contract,
    canonical_test_contract,
)
from app.services.story_service import get_next_sequence
from app.utils.auth_dependency import get_current_user
from app.utils.feature_flags import feature_required
from app.utils.project_authorization import require_project_admin, require_project_member


router = APIRouter(
    prefix="/repositories",
    tags=["Repositories"],
    dependencies=[Depends(feature_required("repository_discovery", "test_registry"))],
)


def local_repositories_enabled() -> bool:
    return settings.enable_local_repositories and settings.app_env.strip().lower() != "production"


def public_repository(doc: dict) -> dict:
    result = {key: value for key, value in doc.items() if key != "_id"}
    if result.get("source_type") == "LOCAL" and not local_repositories_enabled():
        result["local_path"] = None
    return result


async def scan_repository(repository: dict) -> dict:
    now = datetime.now(timezone.utc)
    await db["repositories"].update_one(
        {"repository_id": repository["repository_id"]},
        {"$set": {"scan_status": "scanning", "scan_error": None, "updated_at": now}},
    )
    try:
        commit_sha, tests, detected_framework = await run_in_threadpool(
            static_scan,
            repository["source_type"],
            repository.get("repository_url"),
            repository.get("local_path"),
            repository["branch"],
        )
        status = "completed" if detected_framework != "unsupported" else "unsupported"
        error = None if status == "completed" else "No supported Robot, Playwright Test, or Selenium Java tests were detected."
        discovered_at = datetime.now(timezone.utc)
        documents = [build_test_contract(repository, commit_sha, item, discovered_at) for item in tests]
        await db["discovered_tests"].delete_many({
            "repository_id": repository["repository_id"],
            "source_commit_sha": commit_sha,
        })
        if documents:
            await db["discovered_tests"].insert_many(documents)
        updates = {
            "framework": detected_framework,
            "source_commit_sha": commit_sha,
            "scan_status": status,
            "scan_error": error,
            "test_count": len(documents),
            "last_scanned_at": discovered_at,
            "updated_at": discovered_at,
            "scanner_version": REPOSITORY_SCANNER_VERSION,
            "registry_version": REGISTRY_VERSION,
        }
        await db["repositories"].update_one(
            {"repository_id": repository["repository_id"]}, {"$set": updates}
        )
        return {**repository, **updates}
    except HTTPException:
        raise
    except Exception as exc:
        failed_at = datetime.now(timezone.utc)
        message = str(exc) or "Repository scan failed"
        updates = {"scan_status": "failed", "scan_error": message, "updated_at": failed_at}
        await db["repositories"].update_one(
            {"repository_id": repository["repository_id"]}, {"$set": updates}
        )
        return {**repository, **updates}


@router.get("/options")
async def repository_options(current_user=Depends(get_current_user)):
    return {
        "github_public": True,
        "local_repository": local_repositories_enabled(),
        "frameworks": ["robot", "playwright", "selenium_java"],
    }


@router.post("", response_model=RepositoryResponse)
async def connect_repository(
    request: RepositoryConnectRequest,
    current_user=Depends(get_current_user),
):
    email = current_user["email"]
    await require_project_admin(request.project_id, current_user)
    branch = validate_branch(request.branch)
    if request.source_type == "LOCAL":
        if not local_repositories_enabled():
            raise HTTPException(403, "Local repositories are available only in enabled development environments")
        if not request.local_path:
            raise HTTPException(422, "Local repository path is required")
        validate_local_repository_path(request.local_path)
        provider = "local"
        repository_url = None
        local_path = request.local_path
    else:
        provider = "github"
        repository_url = validate_public_github_url(request.repository_url or "")
        local_path = None

    now = datetime.now(timezone.utc)
    repository = {
        "repository_id": await get_next_sequence("repository_id", "REP"),
        "project_id": request.project_id,
        "source_type": request.source_type,
        "provider": provider,
        "repository_url": repository_url,
        "local_path": local_path,
        "branch": branch,
        "framework": "auto",
        "source_commit_sha": None,
        "scan_status": "scanning",
        "scan_error": None,
        "test_count": 0,
        "last_scanned_at": None,
        "scanner_version": REPOSITORY_SCANNER_VERSION,
        "registry_version": REGISTRY_VERSION,
        "created_by": email,
        "created_at": now,
        "updated_at": now,
    }
    await db["repositories"].insert_one(repository)
    return public_repository(await scan_repository(repository))


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(project_id: str, current_user=Depends(get_current_user)):
    await require_project_member(project_id, current_user)
    cursor = db["repositories"].find({"project_id": project_id})
    return [public_repository(doc) async for doc in cursor]


async def accessible_repository(repository_id: str, current_user: dict, admin: bool = False) -> dict:
    repository = await db["repositories"].find_one({"repository_id": repository_id})
    if not repository:
        raise HTTPException(404, "Repository not found or access denied")
    checker = require_project_admin if admin else require_project_member
    await checker(repository["project_id"], current_user)
    return repository


@router.post("/{repository_id}/rescan", response_model=RepositoryResponse)
async def rescan_repository(repository_id: str, current_user=Depends(get_current_user)):
    repository = await accessible_repository(repository_id, current_user, admin=True)
    if repository["source_type"] == "LOCAL" and not local_repositories_enabled():
        raise HTTPException(403, "Local repositories are disabled in this environment")
    return public_repository(await scan_repository(repository))


@router.get("/{repository_id}/tests", response_model=list[DiscoveredTestResponse])
async def list_discovered_tests(repository_id: str, current_user=Depends(get_current_user)):
    repository = await accessible_repository(repository_id, current_user)
    commit_sha = repository.get("source_commit_sha")
    if not commit_sha:
        return []
    cursor = db["discovered_tests"].find({
        "project_id": repository["project_id"],
        "repository_id": repository_id,
        "source_commit_sha": commit_sha,
    }).sort([("relative_file_path", 1), ("line_number", 1)])
    return [canonical_test_contract(doc, repository) async for doc in cursor]
