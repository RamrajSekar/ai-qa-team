from typing import Literal
from pydantic import Field, create_model
from app.models.approved_visual_run import Contract, RequestKey, Identifier


class KnowledgeQuestion(Contract):
    request_id: RequestKey
    question: str = Field(min_length=3, max_length=2000)


class AnswerCitation(Contract):
    claim_id: Identifier
    quote: str = Field(min_length=1, max_length=1500)


class KnowledgeAnswer(Contract):
    status: Literal["supported", "not_covered", "conflicting"]
    answer: str = Field(min_length=1, max_length=6000)
    citations: list[AnswerCitation] = Field(default_factory=list, max_length=12)


def answer_selection_schema(claim_ids: list[str]):
    """Provider selects current IDs; trusted code supplies the public quote/evidence."""
    reference = create_model("ApprovedClaimReference", __base__=Contract,
        claim_id=(Identifier, Field(json_schema_extra={"enum": claim_ids})))
    return create_model("KnowledgeAnswerSelection", __base__=KnowledgeAnswer,
        citations=(list[reference], Field(default_factory=list, max_length=12)))
