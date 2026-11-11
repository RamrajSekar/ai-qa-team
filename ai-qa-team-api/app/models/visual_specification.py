"""Bounded authoring contracts. Credential inputs use references; literal inputs are public text."""
from typing import Literal

from pydantic import Field, model_validator

from app.models.approved_visual_run import Contract, Identifier, RequestKey, VisibleText, Digest


class StepInput(Contract):
    source: Literal["literal", "parameter", "credential"]
    text: str | None = Field(default=None, max_length=500)
    name: Identifier | None = None
    field: Literal["username", "password"] | None = None

    @model_validator(mode="after")
    def validate_source(self):
        fields = {"literal": "text", "parameter": "name", "credential": "field"}
        selected = fields[self.source]
        if getattr(self, selected) is None:
            raise ValueError("The selected input source requires a value")
        if any(getattr(self, name) is not None for name in ("text", "name", "field") if name != selected):
            raise ValueError("Input sources cannot be combined")
        return self


class VisualStep(Contract):
    action: Literal["navigate", "click", "type", "assert_text", "reusable"]
    target: VisibleText | None = None
    path: str | None = Field(default=None, max_length=240, pattern=r"^/[A-Za-z0-9/_.-]*$")
    value: StepInput | None = None
    expected: VisibleText | None = None
    workflow_version_id: RequestKey | None = None
    inputs: dict[Identifier, StepInput] = Field(default_factory=dict, max_length=20)

    @model_validator(mode="after")
    def validate_action(self):
        required = {"navigate": {"path"}, "click": {"target"}, "type": {"target", "value"},
                    "assert_text": {"expected"}, "reusable": {"workflow_version_id"}}
        allowed = required[self.action] | ({"inputs"} if self.action == "reusable" else set())
        present = {field for field in ("target", "path", "value", "expected", "workflow_version_id")
                   if getattr(self, field) is not None}
        if self.inputs:
            present.add("inputs")
        if not required[self.action].issubset(present) or present - allowed:
            raise ValueError("Fields do not match the selected action")
        if self.path and (self.path.startswith("//") or any(part in (".", "..") for part in self.path.split("/"))):
            raise ValueError("Navigation must stay relative to the approved environment")
        if any(value.source == "parameter" for value in self.inputs.values()):
            raise ValueError("Reusable inputs must be public text or credential references")
        return self


class WorkflowDraft(Contract):
    workflow_id: Identifier | None = None
    title: VisibleText
    steps: list[VisualStep] = Field(min_length=1, max_length=20)


class SpecificationDraft(Contract):
    steps: list[VisualStep] = Field(min_length=1, max_length=40)


class SpecificationPreviewSelection(Contract):
    environment_id: Identifier
    application_role: VisibleText | None = None


class WorkflowReference(Contract):
    workflow_id: Identifier
    version_id: RequestKey
    content_digest: Digest


class CompiledSpecificationPreview(Contract):
    schema_version: Literal["1.0"] = "1.0"
    purpose: Literal["approved-specification-preview"] = "approved-specification-preview"
    target_policy: Literal["salesforce-sandbox-preparation-v1"] = "salesforce-sandbox-preparation-v1"
    execution_ready: Literal[False] = False
    testcase_id: Identifier
    approved_specification_version_id: RequestKey
    specification_digest: Digest
    source_digest: Digest
    workflow_versions: list[WorkflowReference]
    steps: list[VisualStep] = Field(min_length=1, max_length=40)
    environment_id: Identifier
    environment_revision: int = Field(ge=1)
    environment_digest: Digest
    target_url: str
    application_role: VisibleText | None = None
    credential_id: Identifier | None = None
    requires_credentials: bool
    manifest_digest: Digest

    @model_validator(mode="after")
    def compiled_only(self):
        if any(step.action == "reusable" or (step.value and step.value.source == "parameter") for step in self.steps):
            raise ValueError("Compiled steps cannot contain unresolved workflow calls or inputs")
        if not any(step.action == "assert_text" for step in self.steps):
            raise ValueError("Compiled steps require explicit expected results")
        return self
