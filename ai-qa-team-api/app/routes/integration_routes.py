from fastapi import APIRouter, Depends, HTTPException
from app.db.connection import db
from app.utils.auth_dependency import get_current_user
from app.services.integration_service import (
    fetch_github_repos,
    fetch_gitlab_repos,
    fetch_bitbucket_repos,
    import_playwright_tests
)
from pydantic import BaseModel, Field
from app.config import settings
from app.utils.feature_flags import feature_required

class ImportRequest(BaseModel):
    repo_url: str = Field(..., description="Git repo URL")
    branch: str = Field("main", description="Branch to import from")
    project_id: str = Field(..., description="Target project ID")

router = APIRouter(prefix="/integrations", tags=["Integrations"])


SUPPORTED_PROVIDERS = {"github", "gitlab", "bitbucket"}


# ------------------------------------------------------------
# LIST REPOSITORIES
# ------------------------------------------------------------
@router.get("/{provider}/repos")
async def list_repositories(provider: str, current_user=Depends(get_current_user)):
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, "Unsupported provider")

    email = current_user["email"]
    user = await db["users"].find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")

    provider_data = user.get("integrations", {}).get(provider)
    if not provider_data:
        raise HTTPException(400, f"{provider} not connected")

    access_token = provider_data.get("access_token")
    if not access_token:
        raise HTTPException(400, f"No token stored for {provider}")

    if provider == "github":
        return await fetch_github_repos(access_token)

    if provider == "gitlab":
        return await fetch_gitlab_repos(access_token)

    if provider == "bitbucket":
        return await fetch_bitbucket_repos(access_token)

def ensure_list(value):
    if isinstance(value, list):
        return value
    return []

# ------------------------------------------------------------
# IMPORT PLAYWRIGHT TESTS
# ------------------------------------------------------------
@router.post(
    "/{provider}/import",
    dependencies=[Depends(feature_required(
        "playwright_repo_adapter", "story_management",
        "scenario_generation", "test_generation",
    ))],
    include_in_schema=all((
        settings.features.playwright_repo_adapter,
        settings.features.story_management,
        settings.features.scenario_generation,
        settings.features.test_generation,
    )),
)
async def import_playwright_route(
    provider: str,
    req: ImportRequest,
    current_user=Depends(get_current_user)
):
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, "Unsupported provider")

    email = current_user["email"]

    user = await db["users"].find_one({"email": email})
    if not user:
        raise HTTPException(404, "User not found")

    provider_data = user.get("integrations", {}).get(provider)
    if not provider_data:
        raise HTTPException(400, f"{provider} not connected")

    access_token = provider_data.get("access_token")
    if not access_token:
        raise HTTPException(400, f"No stored OAuth token for {provider}")

    # Ensure project exists
    project = await db["projects"].find_one({"project_id": req.project_id})
    if not project:
        raise HTTPException(404, "Project does not exist")

    # Import tests
    try:
        summary = await import_playwright_tests(
            repo_url=req.repo_url,
            branch=req.branch,
            access_token=access_token,
            project_id=req.project_id,
            provider=provider
        )
        scenarios = ensure_list(summary.get("scenarios"))
        testcases = ensure_list(summary.get("testcases"))
    except Exception as ex:
        raise HTTPException(500, f"Import failed: {str(ex)}")

    return {
        "message": "Import completed successfully",
        "summary": summary,
        "imported_scenarios": len(scenarios),
        "imported_testcases": len(testcases),
    }
