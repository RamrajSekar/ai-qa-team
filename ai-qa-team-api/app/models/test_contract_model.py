from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestContract(BaseModel):
    """Canonical framework-neutral record for one test at one repository revision."""

    model_config = ConfigDict(extra="ignore")

    contract_version: str
    registry_version: str
    scanner_version: str
    test_id: str
    project_id: str
    repository_id: str
    source_commit_sha: str
    framework: str
    test_name: str
    relative_file_path: str
    line_number: int | None = None
    tags: list[str] = Field(default_factory=list)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    runtime_dependencies: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str | None = None
    discovered_at: datetime
    updated_at: datetime
