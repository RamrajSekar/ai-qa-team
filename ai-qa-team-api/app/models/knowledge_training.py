"""Pending human review, separate from immutable approved knowledge."""
from typing import Literal
from pydantic import Field, model_validator
from app.models.approved_visual_run import Contract, Identifier, RequestKey, VisibleText
from app.models.product_knowledge import KnowledgeClaim, KnowledgeSourceInput


class TrainingStart(Contract):
    request_id: RequestKey
    title: VisibleText
    mode: Literal["training", "correction", "removal"] = "training"
    source: KnowledgeSourceInput | None = None
    source_id: RequestKey | None = None
    story_id: Identifier | None = None
    claim_id: Identifier | None = None

    @model_validator(mode="after")
    def inputs(self):
        if self.mode == "training":
            if sum(value is not None for value in (self.source, self.source_id, self.story_id)) != 1 or self.claim_id:
                raise ValueError("Choose one source for training")
        elif not self.claim_id or self.source is not None or self.source_id or self.story_id:
            raise ValueError("Choose an approved rule for correction/removal")
        return self


class ReviewProposal(Contract):
    claim: KnowledgeClaim
    decision: Literal["pending", "confirmed", "rejected", "clarify"] = "pending"
    clarification_question: str = Field(default="", max_length=1000)
    clarification_answer: str = Field(default="", max_length=2000)


class TrainingReview(Contract):
    expected_revision: int = Field(ge=0)
    proposals: list[ReviewProposal] = Field(max_length=100)
    clarification_answers: dict[str, str] = Field(default_factory=dict, max_length=30)
    removal_reason: str = Field(default="", max_length=2000)


class TrainingExtract(Contract):
    retry_uncertain: bool = False
    expected_attempt: int | None = Field(default=None, ge=0)


class TrainingSave(Contract):
    expected_revision: int = Field(ge=0)


class TrainingRebase(TrainingSave):
    request_id: RequestKey
