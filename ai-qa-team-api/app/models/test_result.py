"""Shared result envelope; public manual input cannot select an automated mode."""
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from app.models.approved_visual_run import Contract, RequestKey

Verdict = Literal["passed", "failed", "blocked", "needs_review", "cancelled"]
ExpectationId = Annotated[str, StringConstraints(pattern=r"^(step|assertion):[0-9]{1,2}$", max_length=12)]


class ManualResultInput(Contract):
    execution_id: RequestKey | None = None
    version_id: RequestKey
    idempotency_key: RequestKey
    actual_result: str = Field(min_length=1, max_length=5000)
    verdict: Verdict
    verified_expectation_ids: list[ExpectationId] = Field(default_factory=list, max_length=80)
    environment_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,80}$")


class TestResult(Contract):
    schema_version: Literal["test-result-v1"] = "test-result-v1"
    run_id: RequestKey
    execution_id: RequestKey | None = None
    project_id: str
    testcase_id: str
    mode: Literal["manual", "automated"]
    adapter: str
    lifecycle: Literal["completed", "cancelled"]
    verdict: Verdict
    actual_result: str
    verified_expectation_ids: list[str]
    specification: dict
    environment: dict | None = None
    executor_id: str
    executor_display_name: str | None = None
    recorded_at: str
    started_at: str | None = None
    evidence: list[dict] = Field(default_factory=list)


class SelectedCase(Contract):
    testcase_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    version_id: RequestKey


class ManualExecutionInput(Contract):
    title: str = Field(min_length=1, max_length=240)
    release_cycle: str = Field(min_length=1, max_length=2000)
    cases: list[SelectedCase] = Field(min_length=1, max_length=10)
    environment_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,80}$")
    idempotency_key: RequestKey
