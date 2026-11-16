"""Explicit combined story/knowledge review; no public approval identity fields."""
from typing import Literal
from pydantic import Field, model_validator
from app.models.approved_visual_run import Contract, RequestKey
from app.models.requirement_context import RequirementDecision
from app.models.product_knowledge import FindingResolution


class StoryKnowledgeReviewInput(Contract):
    request_id: RequestKey
    analysis_id: RequestKey
    parent_version_id: RequestKey
    timing: Literal["now", "later"] = "now"
    target_release: str = Field(default="Current", min_length=1, max_length=100)
    decisions: list[RequirementDecision] = Field(min_length=1, max_length=40)
    resolutions: list[FindingResolution] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.target_release.strip():
            raise ValueError("Name the target release")
        return self
