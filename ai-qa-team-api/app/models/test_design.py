from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from app.models.approved_visual_run import Contract, VisibleText

Nonblank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ScenarioIntent(Contract):
    title: VisibleText
    description: str = Field(max_length=2000)
    purpose: str = Field(min_length=1, max_length=1500)
    role: str | None = Field(default=None, max_length=100)
    coverage_type: Literal["happy_path", "negative", "boundary", "exception"]
    preconditions: list[str] = Field(max_length=15)
    expected_outcome: Nonblank
    acceptance_criteria_refs: list[str] = Field(min_length=1, max_length=15)
    rule_references: list[str] = Field(max_length=30)


class ScenarioIntents(Contract):
    scenarios: list[ScenarioIntent] = Field(min_length=1, max_length=20)


class ProcedureStep(Contract):
    instruction: Nonblank
    expected: Nonblank


class PublicDataItem(Contract):
    name: VisibleText
    value: Nonblank


class DesignedTestCase(Contract):
    title: VisibleText
    purpose: str = Field(min_length=1, max_length=1500)
    role: str | None = Field(default=None, max_length=100)
    preconditions: list[str] = Field(max_length=15)
    public_data: list[PublicDataItem] = Field(max_length=20)
    procedure: list[ProcedureStep] = Field(min_length=1, max_length=40)
    assertions: list[Nonblank] = Field(min_length=1, max_length=20)
    cleanup: list[str] = Field(max_length=15)
    acceptance_criteria_refs: list[str] = Field(min_length=1, max_length=15)
    rule_references: list[str] = Field(max_length=30)

    @model_validator(mode="after")
    def distinct_data(self):
        if len({item.name for item in self.public_data}) != len(self.public_data):
            raise ValueError("Public data names must be unique")
        return self


class DesignedTestCases(Contract):
    testcases: list[DesignedTestCase] = Field(min_length=1, max_length=20)
