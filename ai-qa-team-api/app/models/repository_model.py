from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SourceType = Literal["GITHUB_PUBLIC", "LOCAL"]


class RepositoryConnectRequest(BaseModel):
    project_id: str
    source_type: SourceType
    repository_url: str | None = None
    local_path: str | None = None
    branch: str = "main"
    framework: Literal["auto", "robot"] = "auto"


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
    created_at: datetime
    updated_at: datetime


class DiscoveredTestResponse(BaseModel):
    test_id: str
    project_id: str
    repository_id: str
    source_commit_sha: str
    framework: str
    test_name: str
    relative_file_path: str
    line_number: int | None = None
    tags: list[str] = Field(default_factory=list)
    discovered_at: datetime
