from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class VisualLabStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    headed: bool = False


class StartupDiagnostics(BaseModel):
    driver_version: str | None = None
    driver_state: Literal['not_started', 'running', 'exited', 'unknown'] = 'unknown'
    driver_exit_code: int | None = None
    browser_state: Literal['running', 'exited', 'not_observed', 'unavailable'] = 'unavailable'
    devtools_port_file: Literal['present', 'absent', 'unavailable'] = 'unavailable'
    session_created: bool = False
    cleanup: Literal['not_started', 'driver_exited_job_closed', 'unverified'] = 'not_started'
    cleanup_driver_exit_code: int | None = None
    cleanup_browser_state: Literal['running', 'exited', 'not_observed', 'unavailable'] = 'unavailable'
    native_errors: list[Literal['access_denied', 'devtools_port_missing', 'browser_exited', 'profile_in_use']] = Field(default_factory=list)


class VisualLabRun(BaseModel):
    run_id: str
    project_id: str
    adapter: Literal['robot-direct-webdriver-smoke-v1'] = 'robot-direct-webdriver-smoke-v1'
    mode: Literal['mechanical-smoke'] = 'mechanical-smoke'
    state: Literal['starting', 'running', 'stopping', 'completed', 'failed', 'cancelled', 'interrupted', 'timed_out']
    headed: bool
    created_at: str
    updated_at: str
    logs: list[str] = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    browser_version: str | None = None
    diagnostic_code: str | None = None
    startup_stage: str | None = None
    startup_reason: str | None = None
    startup_timings_ms: dict[str, int] = Field(default_factory=dict)
    startup_diagnostics: StartupDiagnostics | None = None
