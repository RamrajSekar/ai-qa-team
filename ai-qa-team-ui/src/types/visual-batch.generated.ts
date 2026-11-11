// Generated from visual_batch_model.py; run scripts/export_visual_batch_contract.py. Do not edit.

export type BatchManifest = {
  "schema_version"?: "1.0";
  "batch_id": string;
  "adapter"?: "robot-direct-webdriver-batch-v1";
  "mode"?: "mechanical-smoke";
  "environment"?: "controlled-synthetic-v1";
  "cases": (FixtureCase)[];
  "case_timeout_seconds"?: 90;
  "batch_timeout_seconds": number;
};

export type CaseResult = {
  "case_run_id": string;
  "state"?: "queued" | "starting" | "running" | "stopping" | "completed" | "failed" | "cancelled" | "interrupted" | "timed_out" | "not_executed";
  "verdict"?: null;
  "screenshots"?: ("01-open" | "02-filled" | "03-confirmed")[];
  "evidence_complete"?: boolean;
  "logs"?: (string)[];
  "diagnostic_code"?: string | null;
  "preparation"?: PreparationDiagnostics | null;
  "startup_stage"?: string | null;
  "startup_reason"?: string | null;
  "startup_timings_ms"?: Record<string, number>;
  "startup_diagnostics"?: CaseStartupDiagnostics | null;
  "started_at"?: string | null;
  "finished_at"?: string | null;
};

export type CaseStartupDiagnostics = {
  "driver_version"?: string | null;
  "driver_state"?: "not_started" | "running" | "exited" | "unknown";
  "driver_exit_code"?: number | null;
  "browser_state"?: "running" | "exited" | "not_observed" | "unavailable";
  "devtools_port_file"?: "present" | "absent" | "unavailable";
  "session_created"?: boolean | null;
  "cleanup"?: "not_started" | "driver_exited_job_closed" | "unverified";
  "cleanup_driver_exit_code"?: number | null;
  "cleanup_browser_state"?: "running" | "exited" | "not_observed" | "unavailable";
  "native_errors"?: ("access_denied" | "devtools_port_missing" | "browser_exited" | "profile_in_use")[];
};

export type FixtureCase = {
  "case_run_id": string;
  "specification"?: "synthetic-form-v1";
  "authorization"?: "server-owned-fixture";
};

export type PreparationDiagnostics = {
  "stage": "workspace" | "image_lookup" | "volume_create" | "container_create" | "manifest_copy" | "parent_authorization" | "launch_intent" | "container_start";
  "error_stage"?: "workspace" | "image_lookup" | "volume_create" | "container_create" | "manifest_copy" | "parent_authorization" | "launch_intent" | "container_start" | null;
  "reason"?: "command_timeout" | "process_launch_failed" | "command_failed" | "filesystem_error" | "persistence_error" | "invalid_configuration" | "unknown" | null;
  "timings_ms"?: Record<string, number>;
  "events"?: (PreparationEvent)[];
};

export type PreparationEvent = {
  "stage": "workspace" | "image_lookup" | "volume_create" | "container_create" | "manifest_copy" | "parent_authorization" | "launch_intent" | "container_start";
  "phase": "started" | "completed" | "failed";
  "at": string;
};

export type VisualBatchStart = {
  "schema_version"?: "1.0";
  "idempotency_key": string;
  "case_count": number;
};

export type VisualBatchRun = {
  "schema_version"?: "1.0";
  "batch_id": string;
  "project_id": string;
  "adapter"?: "robot-direct-webdriver-batch-v1" | "robot-direct-webdriver-check-pool-v1";
  "execution_strategy"?: "sequential-batch-v1" | "parallel-checks-v1";
  "mode"?: "mechanical-smoke";
  "state": "queued" | "starting" | "running" | "stopping" | "completed" | "failed" | "cancelled" | "interrupted" | "timed_out";
  "manifest": BatchManifest;
  "cases": (CaseResult)[];
  "created_at": string;
  "updated_at": string;
  "diagnostic_code"?: "ENGINE_UNAVAILABLE" | "DISPATCH_INTERRUPTED" | "IMAGE_UNAVAILABLE" | "BATCH_CONFIGURATION_UNAVAILABLE" | "EVIDENCE_UNAVAILABLE" | null;
  "metering"?: "unbilled-development";
};
