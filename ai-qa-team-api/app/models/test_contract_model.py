from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


KeywordResolutionStatus = Literal["RESOLVED", "UNRESOLVED", "BUILTIN_OR_LIBRARY", "AMBIGUOUS"]
ResourceResolutionStatus = Literal["RESOLVED", "UNRESOLVED", "DYNAMIC", "REMOTE", "OUTSIDE_REPOSITORY"]


class KeywordCallReference(BaseModel):
    sequence: int
    name: str
    arguments: list[str] = Field(default_factory=list)
    source_file: str
    line_number: int | None = None
    resolution_status: KeywordResolutionStatus
    keyword_reference: str | None = None


class ResourceImportReference(BaseModel):
    importing_file: str
    raw_path: str
    resolved_path: str | None = None
    resolution_status: ResourceResolutionStatus


class KeywordDefinitionReference(BaseModel):
    keyword_reference: str
    name: str
    source_file: str
    line_number: int | None = None
    declared_arguments: list[str] = Field(default_factory=list)
    nested_calls: list[KeywordCallReference] = Field(default_factory=list)


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
    steps: list[KeywordCallReference] = Field(default_factory=list)
    resource_imports: list[ResourceImportReference] = Field(default_factory=list)
    keyword_references: list[KeywordDefinitionReference] = Field(default_factory=list)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    runtime_dependencies: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str | None = None
    discovered_at: datetime
    updated_at: datetime
