"""Canonical v1 contracts for synthetic Linux batch execution, not business tests."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.visual_lab_model import StartupDiagnostics

ID = r'^[0-9a-f]{32}$'
State = Literal['queued', 'starting', 'running', 'stopping', 'completed', 'failed', 'cancelled', 'interrupted', 'timed_out', 'not_executed']
BatchState = Literal['queued', 'starting', 'running', 'stopping', 'completed', 'failed', 'cancelled', 'interrupted', 'timed_out']


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class BatchStart(Contract):
    schema_version: Literal['1.0'] = '1.0'
    idempotency_key: str = Field(pattern=ID)
    case_count: int = Field(ge=1, le=10, strict=True)


class FixtureCase(Contract):
    case_run_id: str = Field(pattern=ID)
    specification: Literal['synthetic-form-v1'] = 'synthetic-form-v1'
    authorization: Literal['server-owned-fixture'] = 'server-owned-fixture'


class BatchManifest(Contract):
    schema_version: Literal['1.0'] = '1.0'
    batch_id: str = Field(pattern=ID)
    adapter: Literal['robot-direct-webdriver-batch-v1'] = 'robot-direct-webdriver-batch-v1'
    mode: Literal['mechanical-smoke'] = 'mechanical-smoke'
    environment: Literal['controlled-synthetic-v1'] = 'controlled-synthetic-v1'
    cases: list[FixtureCase] = Field(min_length=1, max_length=10)
    case_timeout_seconds: Literal[90] = 90
    batch_timeout_seconds: int = Field(ge=110, le=1100, strict=True)

    @model_validator(mode='after')
    def unique_cases_and_budget(self):
        if len({c.case_run_id for c in self.cases}) != len(self.cases):
            raise ValueError('Duplicate case-run identity')
        if self.batch_timeout_seconds != len(self.cases) * 110:
            raise ValueError('Invalid synthetic batch budget')
        return self


class CaseStartupDiagnostics(StartupDiagnostics):
    """Missing observations stay unknown without changing the legacy run schema."""
    session_created: bool | None = None
    cleanup: Literal['not_started', 'driver_exited_job_closed', 'unverified'] = 'unverified'


PreparationStage = Literal['workspace', 'image_lookup', 'volume_create', 'container_create',
    'manifest_copy', 'parent_authorization', 'launch_intent', 'container_start']
PreparationReason = Literal['command_timeout', 'process_launch_failed', 'command_failed',
    'filesystem_error', 'persistence_error', 'invalid_configuration', 'unknown']


class PreparationEvent(Contract):
    stage: PreparationStage
    phase: Literal['started', 'completed', 'failed']
    at: datetime


class PreparationDiagnostics(Contract):
    stage: PreparationStage
    error_stage: PreparationStage | None = None
    reason: PreparationReason | None = None
    timings_ms: dict[PreparationStage, int] = Field(default_factory=dict)
    events: list[PreparationEvent] = Field(default_factory=list, max_length=24)


class CaseResult(Contract):
    case_run_id: str = Field(pattern=ID)
    state: State = 'queued'
    verdict: None = None  # Mechanical completion must never become a business pass.
    screenshots: list[Literal['01-open', '02-filled', '03-confirmed']] = Field(default_factory=list)
    evidence_complete: bool = False
    logs: list[str] = Field(default_factory=list, max_length=40)
    diagnostic_code: str | None = None
    preparation: PreparationDiagnostics | None = None
    startup_stage: str | None = None
    startup_reason: str | None = None
    startup_timings_ms: dict[str, int] = Field(default_factory=dict)
    startup_diagnostics: CaseStartupDiagnostics | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class BatchRun(Contract):
    schema_version: Literal['1.0'] = '1.0'
    batch_id: str = Field(pattern=ID)
    project_id: str
    adapter: Literal['robot-direct-webdriver-batch-v1', 'robot-direct-webdriver-check-pool-v1'] = 'robot-direct-webdriver-batch-v1'
    execution_strategy: Literal['sequential-batch-v1', 'parallel-checks-v1'] = 'sequential-batch-v1'
    mode: Literal['mechanical-smoke'] = 'mechanical-smoke'
    state: BatchState
    manifest: BatchManifest
    cases: list[CaseResult] = Field(min_length=1, max_length=10)
    created_at: datetime
    updated_at: datetime
    diagnostic_code: Literal['ENGINE_UNAVAILABLE', 'DISPATCH_INTERRUPTED', 'IMAGE_UNAVAILABLE', 'BATCH_CONFIGURATION_UNAVAILABLE', 'EVIDENCE_UNAVAILABLE'] | None = None
    metering: Literal['unbilled-development'] = 'unbilled-development'


class CheckDispatch(BatchRun):
    """Private durable one-case job contract; never accepted as customer input."""
    parent_batch_id: str = Field(pattern=ID)

    @model_validator(mode='after')
    def one_case_identity(self):
        if len(self.manifest.cases) != 1 or len(self.cases) != 1:
            raise ValueError('A check container owns exactly one case')
        if self.manifest.batch_id != self.batch_id or self.manifest.cases[0].case_run_id != self.batch_id or self.cases[0].case_run_id != self.batch_id:
            raise ValueError('Check dispatch identity mismatch')
        if self.manifest.batch_timeout_seconds != 110:
            raise ValueError('Invalid check container budget')
        return self
