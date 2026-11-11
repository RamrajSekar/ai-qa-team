"""Versioned contracts for synthetic approved visual run admission."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints


Identifier = Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9_-]{1,80}$')]
Digest = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')]
RequestKey = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{32}$')]
VisibleText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class ApproveVisualTest(Contract):
    button_label: VisibleText
    expected_text: VisibleText


class ApprovedVisualTest(ApproveVisualTest):
    version_id: RequestKey
    testcase_id: Identifier
    story_id: Identifier
    scenario_id: Identifier
    knowledge_version: Literal['synthetic-fixture-knowledge-v1'] = 'synthetic-fixture-knowledge-v1'
    source_digest: Digest
    content_digest: Digest
    approved_by: str
    approved_at: datetime
    steps: tuple[Literal['open'], Literal['click_visible_button'], Literal['assert_visible_text']] = (
        'open', 'click_visible_button', 'assert_visible_text',
    )


class VisualRunSelection(Contract):
    approved_test_version_id: RequestKey
    environment_id: Identifier


class StartApprovedVisualRun(VisualRunSelection):
    preview_digest: Digest
    idempotency_key: RequestKey


class ApprovedVisualPreview(Contract):
    schema_version: Literal['1.0'] = '1.0'
    adapter: Literal['approved-visual-synthetic-v1'] = 'approved-visual-synthetic-v1'
    target: Literal['server-owned-synthetic-fixture'] = 'server-owned-synthetic-fixture'
    mode: Literal['synthetic-admission'] = 'synthetic-admission'
    test: ApprovedVisualTest
    environment_id: Identifier
    environment_digest: Digest
    preview_digest: Digest
    max_browser_sessions: Literal[1] = 1
    max_input_actions: Literal[1] = 1
    # Keep the original admission contract readable. The synthetic bitmap
    # executor consumes zero model calls from this allowance.
    max_model_calls: Literal[1] = 1
    timeout_seconds: Literal[90] = 90


class AdmittedVisualRun(ApprovedVisualPreview):
    run_id: Digest
    state: Literal['admitted', 'running', 'cancelling', 'completed', 'cancelled'] = 'admitted'
    verdict: Literal['passed', 'failed', 'blocked', 'needs_review', 'cancelled'] | None = None
    observed_text: VisibleText | None = None
    evidence_available: bool = False
    reason: str | None = None
    execution_adapter: Literal['browserstack-direct-webdriver-v1'] | None = None


class VisualTestRunState(Contract):
    approval: ApprovedVisualTest | None = None
    latest_run: AdmittedVisualRun | None = None
