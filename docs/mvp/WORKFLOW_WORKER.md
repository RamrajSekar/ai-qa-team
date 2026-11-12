# Durable admission and isolated browser-readiness worker

Development continuation, 2026-11-11, on `dev`. Checkpoint commit `9816300` and
[PR #1](https://github.com/RamrajSekar/ai-qa-team/pull/1) contain the preceding
knowledge/admission slice, now merged. The user authorized a separate commit, PR
and merge for this bounded worker continuation. This does not complete tasks 3–7.

## Implemented boundary

The existing UI/API saves an immutable compiled admission. An explicit
**Check isolated browser readiness only** operation queues it in MongoDB. A
separately launched worker claims it and starts a separate Python interpreter:

`API → Mongo admission → worker → isolated Robot core/custom library → HTTPX direct WebDriver → BrowserStack Chrome`

The BrowserStack adapter manages the remote browser/driver; this does not qualify
local Chrome for Testing, Windows fresh installs, Linux containers or five-way
execution. The runner has no Selenium/Playwright/Puppeteer client dependency.

This operation opens **only `about:blank`**. It does not navigate the selected
environment URL, execute approved steps, resolve application credentials, capture
screenshots or call AI. The manifest is consumed as pinned identity, never code.
Robot exposes two fixed readiness keywords. General actions and independent
assertions remain tasks 3/4; credentialed evidence/network protection remains task 5.

Successful readiness records `browser_readiness=ready`, lifecycle `completed`,
verdict **Blocked**, reason `ACTION_RUNTIME_NOT_ENABLED`. It never records a case
pass. A cancelled check records Cancelled. Unconfirmed cleanup requires review
and holds capacity. The existing synthetic execution adapter remains unchanged.

## Admission, dispatch and recovery

- Queue route: `POST /projects/{project_id}/visual-specifications/runs/{run_id}/browser-preflight`.
- Inspect/cancel retain their existing project-authorized run routes. Latest
  admission: `GET /projects/{project_id}/visual-specifications/cases/{testcase_id}/runs`.
  The UI restores it after refresh and uses manual status refresh, not background polling.
- Default-off `approved_workflow_worker`, existing `reusable_workflows` and
  `approved_visual_run_admission` guard queue and worker side effects. Development
  mode is mandatory. The API never launches the worker or browser in its lifespan/request.
- Queue and worker revalidate the keyed manifest, current approved specification,
  exact workflow versions, sources, knowledge/analysis and environment revision/digest.
  Disabling knowledge mode cannot bypass a manifest's knowledge pins.
- Worker resolves the dispatch requester from the users collection and requires
  current project membership before starting. Platform roles do not bypass it.
- Atomic Mongo slot insertion and queued→running comparison-and-set permit one
  BrowserStack readiness operation. The existing synthetic BrowserStack adapter
  shares this slot; its jobs/consumers are not reused. Linux's separate five-slot
  configuration is preserved; this is not unified cross-engine concurrency qualification.
- An execution token fences updates and release. Completed/cancelled operations
  are never requeued/replayed. Interrupted running leases reconcile to terminal
  records; known sessions are closed. An unknown/unconfirmed remote session keeps
  its slot until cleanup is confirmed, rather than expiring on a guessed idle timeout.
- Explicit maintenance: `--reconcile-run RUN_ID` verifies the stored manifest and
  matching slot/token, rejects an active unexpired lease, attempts bounded cleanup
  and releases only that slot. It preserves the original verdict/diagnostic. If no
  session handle exists or the provider cannot confirm closure, capacity remains held;
  operator investigation is required. There is no unsafe force-release endpoint.

Worker work budget is 80 seconds; a stale supervisor is detectable after 120 seconds.
Session creation read budget is 30 seconds; ordinary runner commands use 10 seconds.
Cleanup is separately bounded. These are readiness engineering defaults, not proven
customer workflow budgets. Cancellation polls durable state while the child works;
it terminates the child if needed and closes its known remote session. No whole-run
or action retry occurs. Worker/API flags are process configuration: restart both
after changing them. Disabling only an API process flag does not propagate magically
to an already running separate worker; cancel/stop that worker before reconfiguration.

Provider credentials travel only over private stdin into the runner, not command
arguments, manifests, Redis or public status. Inherited backend environment secrets
are excluded. Session handles/fencing tokens are private Mongo fields and are
allowlisted out of API responses. Robot output is captured/discarded; no raw
provider error, command line or local path enters diagnostics. No application
credential resolution or secret screenshot handling is claimed by this slice.

## Windows setup and manual development run

Use the API's established environment and development MongoDB, with existing
server-side BrowserStack credentials. Do not paste credentials into these commands.
From repository root, set up the separate runner if needed using the existing
`visual-runner/setup.ps1` (Python 3.12); do not install runner dependencies into the
API environment. The readiness mode uses the installed Robot/HTTPX packages and
remote Chrome, so downloaded local browser binaries are not used by this operation.

Set these in **both API and worker terminals**, or the private development backend
environment file; defaults remain off in source:

```powershell
$env:APP_ENV='development'
$env:FEATURES__REUSABLE_WORKFLOWS='true'
$env:FEATURES__APPROVED_VISUAL_RUN_ADMISSION='true'
$env:FEATURES__APPROVED_WORKFLOW_WORKER='true'
$env:VISUAL_RUNNER_PYTHON='F:\ai-qa-team\visual-runner\.venv\Scripts\python.exe'
Set-Location F:\ai-qa-team\ai-qa-team-api
```

API terminal (normal development startup creates existing indexes):

```powershell
..\.feature-flags.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Separate worker terminal:

```powershell
..\.feature-flags.venv\Scripts\python.exe -m app.workers.approved_workflow_worker
# Optional: consume at most one queued readiness operation, then exit.
# ..\.feature-flags.venv\Scripts\python.exe -m app.workers.approved_workflow_worker --once
# Recover one terminated/stale owned run without replay (replace RUN_ID):
# ..\.feature-flags.venv\Scripts\python.exe -m app.workers.approved_workflow_worker --reconcile-run RUN_ID
```

UI terminal: `npm run dev` from `ai-qa-team-ui`, with its normal local API URL.
Sign in normally. In Test Cases, save/review/approve a visual specification,
select environment/optional role, preview, then save an immutable admission.
Its URL still uses the existing restrictive preparation policy; that URL is not
navigated by readiness. Click readiness-only, refresh status, inspect the Blocked
case verdict with readiness ready, then refresh the page to confirm restoration.
Queue another admission and Cancel to exercise cancellation. Ctrl+C stops the
worker and cancels its active readiness operation; hard termination must be
reconciled on restart. Do not use customer data for these development checks.

## Verification commands and evidence

API directory:

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_approved_workflow_worker.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_specifications.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_feature_flags.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_approved_visual_runs.py -v
# Actual development Mongo, random-prefixed isolated collections, synthetic auth/transport:
..\.feature-flags.venv\Scripts\python.exe -X utf8 tests/verify_workflow_worker_real.py
# Opt-in actual BrowserStack session, still synthetic authorization and about:blank only:
..\.feature-flags.venv\Scripts\python.exe -X utf8 tests/verify_workflow_worker_real.py --browserstack
..\.feature-flags.venv\Scripts\python.exe -X utf8 tests/verify_workflow_worker_real.py --cancel-browserstack
```

Runner directory:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_workflow_preflight.py -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m linux.check_dependencies
```

UI: TypeScript/focused lint and `node --test tests/workflow-readiness.test.cjs`.
Use a separate fixture server on port 3123 with
`NEXT_PUBLIC_API_URL=http://feature-api.test`, no real `.env`, and the existing
separate Playwright UI tooling via `PLAYWRIGHT_MODULE_PATH`. This regression
intercepts authentication and APIs; it is not real login or Mongo evidence.

Real Mongo checks passed concurrent idempotency, exact reusable-version pins,
fresh-OS-process persistence read, actual slot contention, cancellation/subsequent
admission with synthetic transport, and stale environment/workflow rejection.
Normal login/API restart and real hard-kill recovery were not run. Simulated
interruption tests are distinct from forced OS termination.

Recorded BrowserStack attempts (sequential; not a reliability qualification):

| Attempt | Operation | Duration | Outcome |
| --- | --- | --- | --- |
| 1 | Readiness | 10,969 ms | Ready; child exited; cleanup acknowledged; before session-event fix |
| 2 | Readiness after stricter cleanup parsing | 6,469 ms | Ready; child exited; cleanup acknowledged; before session-event fix |
| 3 | Cancel probe | 6,578 ms | Completed before cancellation was sent; cancellation NOT EXERCISED |
| 4 | Event-triggered cancel probe | 7,718 ms | Cancellation NOT EXERCISED: Robot captured the private event |
| 5 | Cancel after private-event fix | 9,000 ms | Cancelled; cleanup initially unconfirmed; slot/fixture retained |
| 6 | Cancel after provider confirmation fix | 10,843 ms | Cancelled; runner exited; cleanup confirmed |
| 7 | Final normal readiness control after both fixes | 7,594 ms | Ready; runner exited; cleanup confirmed; case verdict Blocked |

Demonstrated fixes: protocol events now bypass Robot's keyword stdout capture;
a missing session event cannot produce readiness success. BrowserStack's legacy
404 lacks W3C's `error` field after an already-closed session; a generic 404 is
not accepted. A bounded read of the provider's session API can confirm
`status=done` and `reason=CLIENT_STOPPED_SESSION`, consistent with its
[official session API](https://www.browserstack.com/docs/automate/api-reference/selenium/session).
Attempt 5 was independently confirmed closed, its exact fenced slot released,
and only its isolated fixture collections removed. No browser workflow was replayed.

Provider session deletion/status confirmation is not host-level process inspection.
No general test pass, customer login, screenshot redaction, production durability,
exactly-once or multi-host readiness is established. General execution and tasks
3–7 remain incomplete; Windows/five-way reliability issues remain open.

Final focused checks for this continuation: 12 worker lifecycle/security/recovery,
10 specification/admission, 23 feature/history, 13 legacy synthetic run/binding,
and 4 isolated Robot/protocol tests passed (62 total). Runner `pip check` and the
installed-distribution dependency scan passed: Robot 7.5, HTTPX 0.28.1, ten installed
distributions including pip. TypeScript/focused lint passed. The intercepted UI
readiness test passed after an initial 90-second cold-compilation timeout; that
first failure is retained here. Real Mongo additionally passed simulated interrupted
lease recovery without replay and stale-input rejection at worker claim. Simulated
faults do not establish actual OS hard-kill or production recovery.
