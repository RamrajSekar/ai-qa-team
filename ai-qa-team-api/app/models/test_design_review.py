"""Phase 1 reviewed natural-language cases; no automation instructions or selectors."""
from pydantic import Field

from app.models.approved_visual_run import Contract, RequestKey
from app.models.test_design import DesignedTestCase


class TestDesignDraft(Contract):
    case: DesignedTestCase
    parent_version_id: RequestKey | None = None
    idempotency_key: RequestKey
    acknowledge_source_changes: bool = False
