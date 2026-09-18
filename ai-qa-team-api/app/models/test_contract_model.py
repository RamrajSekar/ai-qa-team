from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CallResolutionStatus = Literal[
    "RESOLVED", "UNRESOLVED", "BUILTIN_OR_LIBRARY", "EXTERNAL_LIBRARY", "AMBIGUOUS", "DYNAMIC"
]
ResourceResolutionStatus = Literal["RESOLVED", "UNRESOLVED", "DYNAMIC", "REMOTE", "OUTSIDE_REPOSITORY"]
SourceImportResolutionStatus = Literal[
    "RESOLVED", "UNRESOLVED", "EXTERNAL_LIBRARY", "DYNAMIC", "REMOTE", "OUTSIDE_REPOSITORY"
]
ProvenanceKind = Literal[
    "LITERAL", "VARIABLE_REFERENCE", "PARAMETER", "ARGUMENT", "ASSIGNMENT", "DECLARATION",
    "CALL_RESULT", "MEMBER_REFERENCE", "ENV_ACCESS_EXPRESSION", "UNKNOWN_EXPRESSION", "TRAVERSAL_LIMIT",
]
ProvenanceResolutionStatus = Literal["RESOLVED", "PARTIAL", "AMBIGUOUS", "UNRESOLVED", "DYNAMIC"]
ValueOwnership = Literal[
    "EXTERNAL_INPUT", "STATIC_INTERNAL", "GENERATED_RUNTIME", "ENVIRONMENT", "CREDENTIAL", "UNKNOWN",
]
OwnershipReason = Literal[
    "STATIC_LITERAL_ORIGIN", "CALL_RESULT_ORIGIN", "ENV_ACCESS_ORIGIN", "EXPLICIT_CREDENTIAL_REFERENCE",
    "EXTERNAL_BOUNDARY_ORIGIN", "AMBIGUOUS_ORIGINS", "DYNAMIC_ORIGIN", "UNRESOLVED_ORIGIN",
    "TRAVERSAL_LIMIT", "CONFLICTING_OWNERSHIP", "MEMBER_ORIGIN",
]


class CallReference(BaseModel):
    sequence: int
    name: str
    arguments: list[str] = Field(default_factory=list)
    source_file: str
    line_number: int | None = None
    resolution_status: CallResolutionStatus
    keyword_reference: str | None = None
    callable_reference: str | None = None


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
    nested_calls: list[CallReference] = Field(default_factory=list)


class SourceImportReference(BaseModel):
    importing_file: str
    raw_path: str
    imported_names: list[str] = Field(default_factory=list)
    resolved_path: str | None = None
    resolution_status: SourceImportResolutionStatus


class CallableDefinitionReference(BaseModel):
    callable_reference: str
    name: str
    source_file: str
    line_number: int | None = None
    declared_parameters: list[str] = Field(default_factory=list)
    nested_calls: list[CallReference] = Field(default_factory=list)


class ValueProvenanceRecord(BaseModel):
    provenance_id: str
    expression: str
    evidence_kind: ProvenanceKind
    source_file: str
    line_number: int | None = None
    resolution_status: ProvenanceResolutionStatus
    source_ids: list[str] = Field(default_factory=list)
    callable_reference: str | None = None
    parameter_name: str | None = None


class ValueOwnershipRecord(BaseModel):
    ownership_id: str
    provenance_id: str
    ownership: ValueOwnership
    status: ProvenanceResolutionStatus
    evidence_ids: list[str] = Field(default_factory=list)
    reason_code: OwnershipReason
    source_file: str
    line_number: int | None = None


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
    test_identity: str
    relative_file_path: str
    line_number: int | None = None
    tags: list[str] = Field(default_factory=list)
    steps: list[CallReference] = Field(default_factory=list)
    resource_imports: list[ResourceImportReference] = Field(default_factory=list)
    keyword_references: list[KeywordDefinitionReference] = Field(default_factory=list)
    source_imports: list[SourceImportReference] = Field(default_factory=list)
    callable_references: list[CallableDefinitionReference] = Field(default_factory=list)
    value_provenance: list[ValueProvenanceRecord] = Field(default_factory=list)
    value_ownership: list[ValueOwnershipRecord] = Field(default_factory=list)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    runtime_dependencies: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str | None = None
    discovered_at: datetime
    updated_at: datetime
