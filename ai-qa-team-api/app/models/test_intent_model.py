import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class IntentSource(StrEnum):
    PASTED_BUG = "PASTED_BUG"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ConstraintType(StrEnum):
    DATE_RANGE = "DATE_RANGE"
    RANGE = "RANGE"
    ENUM = "ENUM"
    PATTERN = "PATTERN"
    RELATIVE = "RELATIVE"
    TEXT = "TEXT"


class InputConstraintType(StrEnum):
    EXACT = "EXACT"
    CONSTRAINED = "CONSTRAINED"
    UNSPECIFIED = "UNSPECIFIED"


class AmbiguitySeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"


class IntentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Constraint(IntentModel):
    type: ConstraintType
    value: str | int | float | list[str] | None = None
    start: str | int | float | None = None
    end: str | int | float | None = None
    unit: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_meaning(self):
        if not any(value not in (None, "", []) for value in (self.value, self.start, self.end, self.description)):
            raise ValueError("Constraint must contain a meaningful value, range, or description")
        if self.type == ConstraintType.DATE_RANGE:
            if not isinstance(self.start, str) or not isinstance(self.end, str):
                raise ValueError("DATE_RANGE requires start and end dates")
            try:
                start, end = date.fromisoformat(self.start), date.fromisoformat(self.end)
            except ValueError as exc:
                raise ValueError("DATE_RANGE dates must use YYYY-MM-DD") from exc
            if start > end:
                raise ValueError("DATE_RANGE start must not be after end")
        return self


class WorkflowStep(IntentModel):
    step_number: int = Field(ge=1)
    action: str = Field(min_length=1, max_length=80)
    target: str | None = Field(default=None, max_length=200)
    details: str = Field(min_length=1, max_length=2_000)
    raw_text: str = Field(min_length=1, max_length=2_000)


class IntentInput(IntentModel):
    name: str = Field(min_length=1, max_length=120)
    raw_value: str | None = Field(default=None, max_length=1_000)
    constraint_type: InputConstraintType
    constraint: Constraint | None = None
    confidence: Confidence | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
        if not normalized:
            raise ValueError("Input name must contain letters or numbers")
        return normalized

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.constraint_type == InputConstraintType.EXACT:
            if not self.raw_value:
                raise ValueError("EXACT input requires raw_value evidence")
            if self.constraint is not None:
                raise ValueError("EXACT input must not contain a resolved constraint")
        elif self.constraint_type == InputConstraintType.CONSTRAINED:
            if not self.raw_value or self.constraint is None:
                raise ValueError("CONSTRAINED input requires raw_value evidence and a constraint")
        elif self.constraint is not None:
            raise ValueError("UNSPECIFIED input must not contain a constraint")
        return self


class Ambiguity(IntentModel):
    field: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1_000)
    severity: AmbiguitySeverity


class TestIntentV1(IntentModel):
    source: IntentSource
    schema_version: str
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5_000)
    environment: str | None = Field(default=None, max_length=500)
    preconditions: list[str] = Field(default_factory=list, max_length=50)
    workflow_steps: list[WorkflowStep] = Field(min_length=1, max_length=100)
    inputs: list[IntentInput] = Field(default_factory=list, max_length=100)
    expected_result: str | None = Field(default=None, max_length=5_000)
    actual_result: str | None = Field(default=None, max_length=5_000)
    reported_behavior: str | None = Field(default=None, max_length=5_000)
    ambiguities: list[Ambiguity] = Field(default_factory=list, max_length=50)
    confidence: Confidence

    @model_validator(mode="after")
    def validate_semantics(self):
        if self.source != IntentSource.PASTED_BUG:
            raise ValueError("TestIntentV1 source must be PASTED_BUG")
        if self.schema_version != "1":
            raise ValueError("Unsupported TestIntent schema version")
        numbers = [step.step_number for step in self.workflow_steps]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("Workflow steps must be ordered sequentially from 1")
        names = [item.name for item in self.inputs]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate normalized input names are not allowed")
        return self


class BugInterpretRequest(IntentModel):
    bug_text: str = Field(min_length=1)

    @field_validator("bug_text")
    @classmethod
    def reject_blank_bug(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Bug text is required")
        return value.strip()


class InterpretationMetadata(IntentModel):
    prompt_key: str
    prompt_version: int | str
    prompt_source: str
    schema_version: str = "1"


class BugInterpretResponse(IntentModel):
    test_intent: TestIntentV1
    interpretation_metadata: InterpretationMetadata
