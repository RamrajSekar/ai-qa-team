"""Source-linked knowledge and reviewed story-analysis contracts."""
from typing import Literal

from pydantic import Field, model_validator

from app.models.approved_visual_run import Contract, Identifier, RequestKey, VisibleText


class TranscriptSegment(Contract):
    start_seconds: float = Field(ge=0, le=1800)
    end_seconds: float = Field(ge=0, le=1800)
    text: str = Field(min_length=1, max_length=12000)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_seconds < self.start_seconds:
            raise ValueError("Segment end precedes its start")
        return self


class KnowledgeSourceInput(Contract):
    title: VisibleText
    kind: Literal["document", "recording_transcript"]
    text: str = Field(default="", max_length=60000)
    segments: list[TranscriptSegment] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def source_content(self):
        if self.kind == "document" and (not self.text.strip() or self.segments):
            raise ValueError("A document requires text")
        if self.kind == "recording_transcript" and (not self.segments or self.text):
            raise ValueError("A recording transcript requires timestamped segments")
        if len(self.text) + sum(len(segment.text) for segment in self.segments) > 60000:
            raise ValueError("Source text exceeds the supported bound")
        return self


class KnowledgeClaim(Contract):
    claim_id: Identifier
    category: Literal["terminology", "role", "business_rule", "workflow", "exception", "unknown"]
    statement: str = Field(min_length=1, max_length=1500)
    epistemic_status: Literal["expected", "observed", "inferred", "unknown"]
    source_id: RequestKey
    segment_index: int | None = Field(default=None, ge=0)
    quote: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.statement.strip() or not self.quote.strip():
            raise ValueError("Knowledge statements and source quotes must not be blank")
        return self


class KnowledgeExtraction(Contract):
    claims: list[KnowledgeClaim] = Field(max_length=60)
    clarification_questions: list[str] = Field(max_length=30)


class KnowledgeDraft(Contract):
    title: VisibleText
    claims: list[KnowledgeClaim] = Field(min_length=1, max_length=100)
    parent_version_id: RequestKey | None = None
    clarification_answers: dict[str, str] = Field(default_factory=dict, max_length=30)


class StoryFinding(Contract):
    finding_id: Identifier
    category: Literal["gap", "ambiguity", "missing_detail", "knowledge_conflict"]
    severity: Literal["blocker", "warning"]
    description: str = Field(min_length=1, max_length=1500)
    question: str = Field(min_length=1, max_length=1000)
    criterion_quote: str | None = Field(default=None, max_length=1200)
    knowledge_claim_id: Identifier | None = None


class StoryAnalysisResult(Contract):
    summary: str = Field(min_length=1, max_length=2000)
    findings: list[StoryFinding] = Field(max_length=40)


class FindingResolution(Contract):
    finding_id: Identifier
    decision: Literal["clarified", "dismissed"]
    rationale: str = Field(min_length=1, max_length=2000)


class ReviewStoryAnalysis(Contract):
    resolutions: list[FindingResolution] = Field(max_length=40)
