from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.test_contract_model import TestContract


SourceType = Literal["GITHUB_PUBLIC", "LOCAL"]


class RepositoryConnectRequest(BaseModel):
    project_id: str
    source_type: SourceType
    repository_url: str | None = None
    local_path: str | None = None
    branch: str = "main"
    framework: Literal["auto", "robot", "playwright"] = "auto"


class RepositoryResponse(BaseModel):
    repository_id: str
    project_id: str
    source_type: SourceType
    provider: Literal["github", "local"]
    repository_url: str | None = None
    local_path: str | None = None
    branch: str
    framework: str
    source_commit_sha: str | None = None
    scan_status: Literal["scanning", "completed", "failed", "unsupported"]
    scan_error: str | None = None
    test_count: int = 0
    last_scanned_at: datetime | None = None
    scanner_version: str
    registry_version: str = "test-registry-1"
    created_at: datetime
    updated_at: datetime


DiscoveredTestResponse = TestContract
