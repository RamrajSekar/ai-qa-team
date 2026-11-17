from typing import Literal
from pydantic import Field, model_validator
from app.models.approved_visual_run import Contract, RequestKey, Identifier


class RequirementDecision(Contract):
    finding_id: Identifier | None = None
    decision: Literal["intentional_change", "correct_story", "needs_clarification"]
    rationale: str = Field(min_length=1, max_length=2000)
    action: Literal["add", "replace", "remove"] | None = None
    rule_id: Identifier | None = None
    expected_result: str | None = Field(default=None, min_length=1, max_length=1500)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.rationale.strip():raise ValueError("A reason is required")
        if self.decision=="intentional_change":
            if not self.action or not self.expected_result or not self.expected_result.strip():
                raise ValueError("Intentional changes require an action and explicit expected result")
            if (self.action in ("replace","remove")) != bool(self.rule_id):
                raise ValueError("Replacement/removal selects an existing rule; additions have no existing rule")
        elif self.action or self.rule_id or self.expected_result:
            raise ValueError("Unresolved decisions cannot contain approved changes")
        return self


class RequirementDraft(Contract):
    request_id: RequestKey
    analysis_id: RequestKey
    basis: Literal["approved_change", "story_only_provisional"]
    target_release: str = Field(min_length=1, max_length=100)
    decisions: list[RequirementDecision] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def release_and_basis(self):
        if not self.target_release.strip():raise ValueError("Release/cycle is required")
        if self.basis=="story_only_provisional" and self.decisions:
            raise ValueError("Story-only contexts cannot approve knowledge changes")
        if self.basis=="approved_change" and not self.decisions:
            raise ValueError("Record requirement-change decisions")
        return self


class StoryGenerationApproval(Contract):
    request_id: RequestKey
    analysis_id: RequestKey
