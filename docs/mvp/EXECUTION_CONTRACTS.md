# Visual batch contracts and local dispatcher

Implemented scope: development-only mechanical synthetic batches. No customer tests,
AI, assertions, subscription charging, legacy queue dispatch or
cloud deployment. A completed fixture says **Browser smoke check completed**; its
business verdict is always null. Full MVP approval/test contracts remain targets.

## Canonical definitions and evolution

Canonical Pydantic models: `ai-qa-team-api/app/models/visual_batch_model.py`.
The API exposes them through OpenAPI. `schema_version: "1.0"` identifies wire
structure; `synthetic-form-v1` identifies immutable server-owned fixture content.
They are distinct identities. Every case occurrence gets a new case_run_id.

- BatchStart: version, caller idempotency key (32 lowercase hex), strict integer
  case_count 1-10. Unknown fields, URLs, test IDs, images, scripts and commands are
  rejected. No caller-owned specification or approval boolean is accepted.
- BatchManifest: server-owned batch/case IDs, adapter/mode, fixed synthetic environment,
  pinned fixture references and case/batch limits. Cases are independent copies of
  the same controlled form workflow. Do not claim these are ten different business tests.
- BatchRun/CaseResult: independent lifecycle and evidence per case, null verdict,
  timestamps, safe diagnostics and explicit evidence_complete. Completed batch
  lifecycle is not Passed. Partial/missing evidence is visible independently.

Exporter: `ai-qa-team-api/scripts/export_visual_batch_contract.py`. The committed
`visual-runner/linux/batch-manifest.schema.json` is generated, not manually edited.
Defaults are expanded and required on the runner wire. The runner validates this
schema with a fail-closed, explicitly supported subset, plus unique-case/budget
invariants. It imports no API configuration/dependencies. Unsupported schema keywords
fail build/tests. This is not a general JSON Schema validator. Schema drift tests
exercise the API and isolated runner together.

From repository root:

```powershell
.\.feature-flags.venv\Scripts\python.exe -X utf8 ai-qa-team-api/scripts/export_visual_batch_contract.py
.\.feature-flags.venv\Scripts\python.exe -X utf8 ai-qa-team-api/scripts/export_visual_batch_contract.py --check
```

Breaking changes require a new explicitly supported schema/adapter version and
compatibility fixtures. Preserve stored manifests/results. Additive fields require
exported-schema/runner/client compatibility review because v1 rejects unknown fields;
do not assume optional additions are automatically forward-compatible. UI types are now generated from the same models into
`ai-qa-team-ui/src/types/visual-batch.generated.ts` by the exporter above. Its --check
and the contract unit suite detect drift in both JSON Schema and TypeScript outputs. Future approved business specifications must carry
story/criteria/knowledge/approval/assertion references; v1 does not impersonate those
missing governance records or grant customer execution.

## Approved visual run contract (design)

2026-11-10. This describes the next synthetic-first path. The existing
`mechanical-smoke` batch manifest remains a separate contract.

### Existing inputs and approval gap

- Onboarding's [environment step](../../ai-qa-team-ui/src/components/onboarding/steps/StepEnvironment.tsx)
  reuses environment management. [EnvironmentModal](../../ai-qa-team-ui/src/components/environment/EnvironmentModal.tsx)
  saves `base_url` through the environment API. Resolve the selected `env_id`
  within the project. A saved URL alone grants no execution permission.
- [Test generation](../../ai-qa-team-api/app/routes/testcase_routes.py) checks
  scenario approval. The [test case model](../../ai-qa-team-api/app/models/test_case_model.py)
  holds steps and a mutable status alongside legacy Playwright code. Scenario
  approval and `ready` status do not establish approval of an immutable test revision.
  Preserve the existing generator and introduce explicit visual specification approval.
- [Visual batch routes](../../ai-qa-team-api/app/routes/visual_batch_routes.py)
  provide the project membership pattern for create, status, cancel and artifacts.
  Reuse that boundary and preserve distinct adapter and mode identity.

### Inputs and lifecycle

| Boundary | Required inputs and behavior |
|---|---|
| Approval | Store an immutable visual test version with project and case identity, story ID, exact acceptance criteria references and approved knowledge version. Pin explicit expected text, the ordered action list, reviewer identity/time and a content digest. If an input is missing or has an unresolved material conflict, approval is unavailable. Editing creates a successor. Use seeded, explicitly identified synthetic knowledge fixtures in admission tests while the product knowledge approval path is pending. |
| Start | Project is part of the authorized route. Accept only `approved_test_version_id`, `environment_id`, `preview_digest` and `idempotency_key`. Reject extra fields. The server issues the digest from the preview's resolved inputs and rejects a new start if they changed. The first synthetic slice binds the environment to the server-owned fixture and displays that resolved target in the preview. |
| Resolve | Scope every lookup to the project, validate the active approval and current environment revision, and pin the resolved target policy, environment revision or immutable snapshot digest, adapter, test and knowledge versions, and limits. Repeat the admission check if preview inputs changed. Keep credentials and raw environment configuration out of the job envelope. |
| Execute | Support only open approved target, locate and click one visible button by label, and assert exact visible text in a separate observation. One session, one click, bounded model/observation budgets and no replay of an uncertain click. Never compile legacy selectors or generated Playwright code into this mode. |
| Report | Keep lifecycle separate from verdict. `Passed` requires the explicit assertion to be evaluated and satisfied. Reliable contradictory evidence yields `Failed`, unavailable prerequisites yield `Blocked`, ambiguous evidence yields `Needs review`, and deliberate cancellation yields `Cancelled`. Attach scoped, retained evidence and a sanitized reason. Mechanical fixture completion cannot become a business verdict. |

For synthetic admission, test authorized success and exact pinned identities,
disabled mode, cross-project test/environment/artifact IDs, missing or stale
approval, missing expectation, unexpected URL/command fields, repeated key with
identical inputs, repeated key with different inputs, and a preview invalidated
by an environment edit. Reject invalid requests before leasing a slot or making a
model call. Check existing synthetic batch/history clients for compatibility.

Staging activation additionally requires an explicitly authorized environment and
enforced network policy covering DNS, redirects and subresources, with private
and metadata destinations blocked. Verify provider permission for staging
screenshots and restrict the first action to reviewed synthetic data with no login
secrets or consequential submission. A staging label in onboarding is insufficient.

### Task 2 backend admission slice

The development-only `approved_visual_run_admission` flag defaults off.
Under `/projects/{project_id}/approved-visual-runs` the backend exposes:

- `POST /testcases/{testcase_id}/approve` for project administrators. The reviewer
  supplies the visible button label and expected text. The server fixes the three
  allowed actions, records the story criteria snapshot and pins an explicitly
  synthetic knowledge identifier. Approval inserts an immutable version and
  updates a separate active-version pointer. Source edits require reapproval.
- `POST /preview` for project members. It resolves the exact approval and
  environment and returns the server-owned fixture target and a preview digest.
  The saved URL and credentials are excluded from the response and run record.
  An authenticated environment digest detects configuration edits.
- `POST /` for project members (the collection path without a trailing slash).
  A matching preview admits one durable record. The Mongo `_id` scopes
  idempotency to project, requester and key. A duplicate with the same input
  returns the original record. A different input with the same key conflicts.

`admitted` is an intake state with a null verdict. There is no consumer for this
collection. Artifact endpoints belong to the execution task.
A future dispatcher must recheck approval, environment revision and execution
policy immediately before leasing or launching. Admission does not make the
separate source collections and admission insert a single Mongo transaction.

### Task 3 project UI and admission lifecycle

With `FEATURES__APPROVED_VISUAL_RUN_ADMISSION=true` and test generation enabled
in a development API, open the project overview and select a test case under
**Approved visual run**. An administrator can approve the label and expected
text. A member can select a saved environment, review the controlled synthetic
target and ordered steps, then admit a run.

- `GET /testcases/{testcase_id}` under the admission route returns the active
  approval and latest run for the selected case so the panel can reopen them
  after a refresh.
- `GET /{run_id}` reads a project-scoped run. `POST /{run_id}/cancel` atomically
  changes an admitted record to cancelled. A repeated cancel returns the
  cancelled record. These operations do not control browser processes yet.
- BrowserStack Actions diagnostics are manual-only in this workflow revision.
  Approved product execution will be started by the project UI through the
  authorized backend when a separately gated execution consumer exists.

Task 3 verification used seven ASGI tests with database/authentication doubles
and one intercepted Edge workflow test. The Edge test covers approval, environment
selection, preview, admission, reload, cancellation and the disabled flag.
Run it with the same external Playwright tooling as the batch UI test, using
`node --test tests/approved-visual-runs.test.cjs`. Its default fixture URL is
`http://127.0.0.1:3123`. Use the intercepted `NEXT_PUBLIC_API_URL=http://feature-api.test`
configuration. No real login, MongoDB, BrowserStack, model call or browser
execution against the controlled sample was exercised by these tests.

### Task 4 single-session development execution

Use the API's existing development environment. Enable
`FEATURES__TEST_GENERATION=true`, `FEATURES__APPROVED_VISUAL_RUN_ADMISSION=true`,
and `FEATURES__APPROVED_VISUAL_RUN_EXECUTION=true`. Supply
`BROWSERSTACK_USERNAME` and `BROWSERSTACK_ACCESS_KEY` in the backend's private
environment or ignored local settings file. The API uses its existing HTTPX and
Pillow requirements. Use one API process for development and restart it after
configuration changes.

1. Open the project overview in the UI, choose a case tied to an approved
   scenario and story with acceptance criteria, and select a saved environment.
2. As an administrator, approve button label **Save draft** and expected text
   **Draft saved**. Preview and admit the synthetic run.
3. Click **Start synthetic browser run**, then **Refresh status** to view the
   verdict and screenshot. A negative control can approve an intentionally
   incorrect expected string. Cancel a running request to ask the worker to
   stop at its next checkpoint and close the remote session.

Launch is explicit through `POST /{run_id}/start`. The development API
revalidates membership, the approval and the environment preview digest.
A Mongo singleton lease limits this execution path to one active remote
session. The worker uses a fixed BrowserStack WebDriver endpoint and an offline
server-owned data page. The selected environment's URL is never opened.
It uses one coordinate click and no model calls. Fixed raster templates
recognize the synthetic button across two styles and several positions,
then independently read the rendered result in a new screenshot. This
fixture-specific detector is separate from general visual targeting.

Run records store one bounded, private screenshot for success or diagnostic
evidence. The project-authorized `GET /{run_id}/evidence` endpoint serves it.
The worker never retries a click. If session cleanup cannot be confirmed, it
retains the slot until the four-minute lease expires and relies on the provider's
60-second idle timeout for unattended sessions. Interrupted runs reconcile on
status read after lease expiry and are never replayed. These bounds are
development controls. They do not establish distributed or hosted reliability.
Starting a run in the UI does not dispatch a GitHub Actions workflow.

Local verification covered eight ASGI tests with doubles, three browser
protocol/PNG tests with doubles, two actual local Edge fixture renders
with screenshot-derived clicks, and one intercepted Edge UI workflow.
The real development login/API/MongoDB/BrowserStack path remains unverified.

## Routes and authorization

Under `/projects/{project_id}/visual-lab/batches`:

| Operation | Behavior |
| --- | --- |
| POST base | Queue a server-owned synthetic manifest; 202, idempotent |
| GET base | Latest 20 project batches |
| GET /{batch_id} | Persisted batch and case state |
| POST /{batch_id}/cancel | Cancel queued batch or request bounded container stop |
| GET /{batch_id}/cases/{case_id}/artifacts/{artifact_id} | Authorized private PNG |

Both `visual_runner_lab` and new default-off `visual_runner_batches` must be enabled,
and app_env must be development/local/test. Existing authentication and project
membership apply to every operation, including artifacts. Cross-project batch IDs
do not resolve. Artifact IDs are only 01-open/02-filled/03-confirmed; no filesystem
path input, raw engine output or private dispatch fields are returned. PNGs are
privately copied to backend-local storage, signature/size checked and served no-store.

Idempotency uniqueness uses Mongo's built-in _id: hash(project, requesting member,
idempotency key). Same key/count returns the original run; changed count gives 409.
This deduplicates initiation, not external UI effects. The account scope currently
uses the project's existing created_by billing-owner convention, never a request
field or the initiating member's separate allowance. Organization migration remains
future work. Synthetic mode is explicitly unbilled-development and changes neither
legacy usage counters nor subscription allowances.

## Durable local orchestration — check pool revision (2026-11-02)

New public BatchRun records use adapter `robot-direct-webdriver-check-pool-v1`
and execution_strategy `parallel-checks-v1`. Existing records default to
`sequential-batch-v1` and retain their original adapter/manifest. BatchStart and
artifact URLs are unchanged. The immutable v1 fixture manifest still groups cases;
it is not a claim that a container runs that entire parent manifest.

Each new parent materializes deterministic queue records in additive
`visual_batch_checks`, keyed by case_run_id and linked privately to parent_batch_id.
Each child dispatches the existing validated v1 runner manifest with exactly one
case, batch_id=case_run_id and a 110-second outer budget (90-second case budget).
No runner dependency/protocol change or image rebuild is needed. One immutable
image, volume, supervisor/sample/profile and container per check. The existing
network-none, non-root, enabled sandbox and per-container resource bounds remain.

The host-bound `local-linux-check-pool-v1` Mongo ledger owns check slots.
VISUAL_BATCH_GLOBAL_SLOTS, VISUAL_BATCH_ACCOUNT_SLOTS and VISUAL_BATCH_PROJECT_SLOTS
accept 1-10 and default to 5. Global capacity is always authoritative. Lowering
capacity reconciles existing higher slots before permitting replacements. A batch
of five can occupy all five; two batches share capacity with oldest queue heads
and last-account/project/batch rotation. Queue-head selection is bounded to 100;
this is local fairness, not a production starvation guarantee.

The existing kernel lock serializes the local controller. Legacy two-slot ledger
containers and old queued batches drain before any new check pool launch. Old
Windows starts remain gated in batch mode; old history/artifacts remain accessible.
No legacy queue is used and no stored manifests are backfilled or reapproved.

Slot claims and child starting state are persisted before independent container
preparation; start_intent is persisted before the single start command. All slots
are reserved before parallel preparation, avoiding sequential-start overhead.
Restart inspects ownership and never starts an old identity again. Missing jobs
after start_intent hold slots; unstarted owned identities can be fenced by removal.
Containers must be exited/PID-zero and reconciled before releasing their slots.
Materialization uses insert-only upserts: partial insertion is recoverable without
resetting child lifecycle. This is single-host/checkout coordination, not distributed
fencing, exactly-once execution or production durability.

Each case collects sanitized state and three fixed PNGs independently. Batch
aggregation preserves ordering and independent outcomes; a case failure does not
stop others. Batch cancel stops all active check containers, cancels queued checks
and preserves completed evidence. Feature-off/shutdown reconciliation remains active
when Podman is configured. Retain engine settings across restarts. Private artifact
layout and project authorization are unchanged; raw logs/profiles are not published.

Per-case budgets remain unchanged. The parent 110*case_count bound is an aggregate
runtime envelope, not queue-wait SLA or a customer spending policy. Entitlement,
shared customer-data locks, environment quotas, billing and multi-host fencing are
not implemented by this synthetic slice. Five containers each capped at 2 GiB/2CPU
do not reserve ten GiB/ten CPUs; measured host capacity must support actual demand.

## Windows developer setup and tests

No cloud credentials or normal Chrome installation are needed. Existing API services
must be development-only. From repository root:

```powershell
podman build --platform linux/amd64 -f visual-runner/linux/Dockerfile -t ai-qa-m1a-linux:batch visual-runner
podman image inspect localhost/ai-qa-m1a-linux:batch --format '{{.Id}}'
# In the API terminal, configure developer-owned paths and the exact ID printed above:
$env:APP_ENV='development'
$env:FEATURES__VISUAL_RUNNER_LAB='true'
$env:FEATURES__VISUAL_RUNNER_BATCHES='true'
$env:VISUAL_BATCH_PODMAN="$env:LOCALAPPDATA\Programs\Podman\podman.exe"
$env:VISUAL_BATCH_IMAGE='<immutable image ID>'
# Start the existing API from ai-qa-team-api using its established environment.
```

The existing project Visual Runner Lab now includes batch controls when both flags
are enabled: choose 1-10 synthetic checks, start/resolve a submission, inspect ordered
cases/evidence and cancel a batch. The old start control is hidden while batch mode
owns capacity, but old history/cancel/evidence remain. Customer application URLs are
not used. Alternatively use authenticated API tooling with existing normal
development login cookies (never forge a token), POST JSON
`{"schema_version":"1.0","idempotency_key":"<32 lowercase hex>","case_count":2}`.
Do not put credentials in shell arguments or committed fixtures. With the batch flag off, the Lab retains the existing single-smoke controls.
Reload the UI after restarting the API with changed flags.

Focused tests (from ai-qa-team-api):

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_batches.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_lab.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_feature_flags.py -v
```

Real opt-in backend fixture (repository root):

```powershell
.\.feature-flags.venv\Scripts\python.exe -X utf8 ai-qa-team-api/tests/run_visual_batch_real.py --podman "$env:LOCALAPPDATA\Programs\Podman\podman.exe" --image '<immutable image ID>' --output tmp/batch-real-new-directory
```

Requires local MongoDB executable, existing cryptography/Motor/API packages and running
Podman. It creates a private task-owned TLS Mongo, synthetic projects/memberships,
actual containers and retained evidence. It does not read .env or change existing
services/data. Authentication is an explicit ASGI double; project authorization,
Mongo persistence, dispatch, browser and artifact operations are real. No UI/normal
login, full API process restart, multi-host or cloud claim follows. Retain failures
and distinguish fixture errors from browser/dispatcher errors in the evidence report.

Next: real development-login qualification for the batch UI; independent process/restart/fencing and
host resource fault qualification; scoped entitlements/usage ledger and approved
customer test contracts. Windows startup blocker and M1B gate remain unchanged.


## Recorded verification

See [dispatch evidence summary](evidence/linux-batch-dispatch-summary.json),
[full post-fix fixture](evidence/linux-batch-real-full.json) and
[final focused fixture](evidence/linux-batch-real-final.json). Each successful fixture
passed 10 checks; the full run completed 10/10 cases in the boundary batch. The final
focused run additionally exercised real Mongo slot contention and disabled-feature
controller startup; it did not repeat the ten-case test. Initial TLS fixture and
cancellation-state failures are retained separately. A cancellation-state regression
is covered by test_linux_spike.py. No real-login/UI or production claim follows.


## Batch UI verification and operation (2026-11-02)

Open `/projects/<project-id>/visual-lab` after normal development sign-in. Existing
feature flags remain off by default; restart the API with both flags enabled and
configured Podman/image settings above, then reload the UI. The page selects only
the controlled sample: onboarding/environment URLs and generated test cases are not
passed to execution. The number 1-10 denotes repetitions of the same synthetic form.
The start button remains available while other batches run, allowing additional
batches to queue; the backend owns global/account/project capacity enforcement.

The UI shows latest 20 project batches, ordered case states/completion counts,
fixed diagnostic codes, partial evidence warnings and lazily loaded private PNGs.
It distinguishes failed/blocked access from empty history. No per-batch global slot
count is invented from project-local history. History pagination is not implemented.
Batch polls run every two seconds only while queued/active work is visible; hidden
tabs pause interval requests, visibility regain/manual Refresh reloads history.
Existing single-smoke polling also stops when idle and pauses while hidden.

A pending start stores only count/idempotency key in sessionStorage scoped to the
signed-in member and project. After network uncertainty or page refresh, explicit
Resolve submitted batch reuses that key; there is no automatic POST retry/replay.
It is a repeat of the idempotent initiation request, not a rerun of browser actions.
Another member/project does not inherit the pending submission. If browser storage
is unavailable, in-memory protection still applies until navigation; manually inspect
history after reconnecting before starting anything else. Read requests have a
10-second client timeout; start confirmation has 20 seconds, cancel confirmation 10.
These do not modify runner/browser deadlines or establish cancellation SLAs.

Current regression evidence: [UI report](evidence/visual-batch-ui-nov02.json).
Nine distinct intercepted UI checks passed across an 8/9 prepared suite and a 1/1
focused correction. The failed assertion counted Strict Mode's aborted duplicate
image transports; it now checks unique artifact identities. Initial fixture startup
also exceeded first navigation timeout (Ready in 183.2s); startup failure is retained.
These are not real-login/Mongo/Podman end-to-end results. Prior real backend evidence
above remains separate and was not rerun in this UI task.

UI regression commands (two terminals, from ai-qa-team-ui; use an unused port and
wait for Ready plus successful Lab route compilation before starting tests):

```powershell
# Terminal 1: task-owned fixture; never substitute a production API.
$env:NEXT_PUBLIC_API_URL='http://feature-api.test'
.\node_modules\.bin\next.cmd dev --webpack --hostname 127.0.0.1 --port 3121
# Terminal 2: existing external Playwright tooling, outside visual-runner dependencies.
$env:PLAYWRIGHT_MODULE_PATH='C:\path\to\node_modules\playwright'
$env:FEATURE_UI_URL='http://127.0.0.1:3121'
node --test --test-concurrency=1 tests/visual-lab.test.cjs tests/visual-batches.test.cjs
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
.\node_modules\.bin\eslint.cmd 'src/components/visual-lab/*.tsx' 'src/components/providers/FeatureFlagsProvider.tsx' 'src/app/(app)/projects/[projectId]/visual-lab/page.tsx'
```

For normal local UI use NEXT_PUBLIC_API_URL=/api and API_BACKEND_URL=http://127.0.0.1:8000
with the established development API setup, not the intercepted fixture URL. No
new dependency, normal Chrome change, runtime flag enablement, .env edit or deployment
was performed for this task. The full real-login new-batch path remains a next gate.


Final UI static checks: TypeScript passed, focused lint passed with zero warnings,
generated JSON/TypeScript drift and git diff --check passed (existing CRLF notices).


## Per-case startup observations (2026-11-02)

CaseResult adds optional sanitized startup stage/reason/timings and the existing
typed StartupDiagnostics bundle. The runner input schema is unchanged. The exporter
handles typed timing dictionaries and emits the updated UI types; use its --check
and contract tests for drift. This coordinated development API/UI response addition
requires no stored-record migration. Older clients can omit these optional fields.

Within View evidence, expand Startup diagnostics. Future cases persist sanitized
values; old cases can show the same data from retained backend-local IPC without
altering historical Mongo records or contacting/replaying the runner. If IPC is
unavailable, the UI says so. A successful rerun is a separate observation and cannot
make an earlier timeout a success or prove a startup fix. No read/session deadline
or retry change was made. Restart the API and reload the UI; no image rebuild.

Focused no-browser presentation command (from ai-qa-team-ui):

```powershell
node --test tests/startup-evidence.test.cjs
```

The existing browser fixture suite now also contains a startup-observation case;
that newly added case was not executed in this observability task. Current actual
checks and limits are in M1A notes and evidence/batch-startup-display-nov02.json.

The case-specific diagnostic subtype keeps missing session observations null/Unknown
and missing cleanup unverified, preserving the legacy single-smoke schema. Final
checks: 11 contract/API tests, two presentation checks, TypeScript, focused lint,
export drift and git diff --check passed. No new runner/browser execution occurred.


## Per-check pool setup and qualification commands

Restart the API after configuration changes (both existing development flags and
the immutable VISUAL_BATCH_IMAGE/Podman path remain required):

```powershell
$env:VISUAL_BATCH_GLOBAL_SLOTS='5'
$env:VISUAL_BATCH_ACCOUNT_SLOTS='5'
$env:VISUAL_BATCH_PROJECT_SLOTS='5'
```

Reload the existing Lab, submit five checks, and observe individual active/queued
counts. The page identifies new Parallel check pool batches and preserves legacy
sequential history. The API's caps are authoritative; the UI does not assign slots.
No browser image rebuild is needed for this controller change. Existing explicitly
configured caps of two still restrict the pool until changed.

Opt-in private TLS Mongo/Podman qualification from repository root:

```powershell
.\.feature-flags.venv\Scripts\python.exe -X utf8 ai-qa-team-api/tests/run_visual_check_parallel_real.py --podman 'C:\Users\ram\AppData\Local\Programs\Podman\podman.exe' --image '<immutable batch image ID>' --output tmp/parallel-five-new-directory
# Separate one-browser control; cannot qualify five-browser concurrency:
.\.feature-flags.venv\Scripts\python.exe -X utf8 ai-qa-team-api/tests/run_visual_check_parallel_real.py --podman 'C:\Users\ram\AppData\Local\Programs\Podman\podman.exe' --image '<immutable batch image ID>' --output tmp/parallel-one-new-directory --quick
```

The fixture uses actual Mongo/containers/Robot/HTTPX/CfT and project membership
queries, with an explicit ASGI authentication double. Browser observations use
bounded read-only in-container probes recording session-live intervals on the same VM clock;
queued/running database records alone do not prove overlap. Missing/nonoverlapping observations
do not qualify concurrency and do not prove that sessions never existed. The revised
interval observer was not run against the real engine in this task. Original
failures are retained; no whole-workflow retries or expanded deadlines are used.


## Current per-check verification result (2026-11-03)

Preparation diagnostics are implemented as optional typed CaseResult.preparation:
stage, first error_stage/reason, bounded timings and timestamped events. The engine
persists progress before commands; reconciliation and parent aggregation preserve
the original error. No raw paths/output/arguments are exposed. Existing records
remain unchanged, with no synthetic historical timeline. This is an additive API/
generated UI contract change; the runner input/image is unchanged.

Latest actual checks: two separate one-case controls completed (2/2); all five
checks in the five-case attempt prepared/started, but only 4/5 completed. One
ChromeDriver session-not-created response and the five-session overlap gate remain
unresolved. Five-case cancellation, terminal/PID0 containers and empty slots were
verified. An explicit missing-image fault preserved image_lookup/command_failed
through actual private Mongo/reconciliation/API. This proves diagnostic retention,
not the cause of the historical c733... failure. See M1A's 2026-11-03 section and
its three evidence reports. Earlier Nov02 failures remain historical evidence.

Use View evidence -> Container preparation after restarting the development API
and reloading the UI. Quick qualification now includes deliberate missing-image
fault injection followed by one normal control, all three private screenshots and
capacity release. Normal login/UI and full API-process restart were not qualified;
real fixtures use explicit authentication doubles. No M1B/customer readiness claim.


## Linux M1B planning gate (2026-11-03)

DECISIONS A14 permits a bounded Linux M1B experiment while Windows and Linux
five-way reliability remain open. The five-slot pool/one-container-per-check design
and ten-case batch boundary remain unchanged. Current fixture contracts do not
already support visual proposals or independent assertions; define those bounded
contracts in the next explicit implementation task, preserving existing adapters,
identities, default-off gates, authorization and history. Do not execute M1B inputs
through the fixed mechanical-fixture contract or silently add arbitrary actions.
No schema export/runtime change is made in this scope-recording task.

### Staging binding contract v1 — preparation only, 2026-11-10

The existing synthetic admission/run contract is preserved. A separate
`approved_staging_bindings` collection holds immutable, non-executable preparation
snapshots. This is Step 2 of staging login preparation; it does not implement a
login specification, a browser adapter, network enforcement or a staging verdict.
Existing approved versions still use the bounded synthetic approval shape; binding
one preserves its identity without qualifying it as an executable login workflow.

Project-authorized, development-only endpoints under approved-visual-runs:

- POST `/staging-bindings/preview` accepts approved_test_version_id, environment_id
  and application_role. The service resolves all fields within the project.
- POST `/staging-bindings` additionally accepts the returned binding_digest and a
  32-hex idempotency_key. Matching retries return the original snapshot. Reusing
  the key for different inputs rejects. Mongo's unique _id prevents duplicate saves.
- GET `/staging-bindings/{binding_id}` returns the immutable snapshot with current
  or stale validation. GET `/staging-bindings/testcases/{testcase_id}` restores the
  most recent snapshot for that project/case. The latest lookup is a metadata query,
  not a reservation or a guarantee of future dispatch validity.

Snapshots pin canonical target URL/origin, target policy identity, environment
revision and keyed digest, application role and opaque credential ID, exact approved
test version/content digest, and source digest. They include no usernames, passwords,
tokens, ciphertext, notes, variables or raw environment document. The server never
resolves/decrypts passwords in this path. Validation errors omit submitted values.

The accepted preparation URL is HTTPS test.salesforce.com, port 443/default, with
root or /login path. An exact hostname without a scheme is normalized to HTTPS.
Other domains/ports, credentials in URLs, query strings, fragments, whitespace and
backslashes reject. This validates a saved target string; DNS, redirects,
subresource traffic and browser egress are not enforced or exercised by this step.

A saved environment must have revision >=1 and a configured encrypted credential
with stable identity for the selected role. Legacy plaintext credentials require
an authorized save first. Changes to environment data, role/credential identity,
secret envelope, test/scenario/story sources or active approval make the binding
stale. A stale snapshot is preserved and requires explicit new preview/preparation.
No failed/interrupted operation is replayed as browser activity.

Every snapshot carries execution_ready=false. There is no staging start endpoint,
job, slot reservation, worker, provider/model call or credential delivery. A binding
ID cannot start through the synthetic run endpoint. The existing synthetic target
and executor remain sample-only. Browser hosting, approved login actions,
provider permissions, egress, redaction and runtime revalidation are later gates.

Checks use database/authentication doubles. Thirteen ASGI approved-run/binding
tests passed in the initial Step 2 run. Live UI/Mongo, real Salesforce traffic,
multi-host races and production durability are unverified. Run
`python -X utf8 -m unittest discover -s tests -p test_approved_visual_runs.py -v`
from ai-qa-team-api. TypeScript/lint use the existing UI commands.

### General specifications and optional reusable workflows, 2026-11-10

[Approved workflows](APPROVED_WORKFLOWS.md) supersedes the mandatory-login authoring
assumption. Canonical inputs and compiled preview contracts are in
app/models/visual_specification.py. Project-scoped versioned drafts, approval,
parameter expansion, dependency review and environment preview are implemented
behind reusable_workflows. Public cases omit role/credentials. New specifications
are distinct from the synthetic approval/binding schema and are not consumed by
existing execution workers. Compiled previews are non-executable and do not admit
runs. General dispatcher/interpreter and real browser qualification remain pending.
