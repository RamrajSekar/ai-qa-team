"""Phase 1 reviewed natural-language cases; no automation instructions or selectors."""
from pydantic import Field

from app.models.approved_visual_run import Contract, RequestKey
from app.models.test_design import DesignedTestCase
from app.models.test_design import Nonblank


class ReviewedTestCase(DesignedTestCase):
    """Human review needs per-step expectations; extra checks/source links are optional."""
    assertions: list[Nonblank] = Field(default_factory=list, max_length=20)
    cleanup: list[str] = Field(default_factory=list, max_length=15)
    acceptance_criteria_refs: list[str] = Field(default_factory=list, max_length=15)
    rule_references: list[str] = Field(default_factory=list, max_length=30)


class TestDesignDraft(Contract):
    case: ReviewedTestCase
    parent_version_id: RequestKey | None = None
    idempotency_key: RequestKey
    acknowledge_source_changes: bool = False
