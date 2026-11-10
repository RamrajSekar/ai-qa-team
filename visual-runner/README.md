# M1A Visual Runner Lab — Windows development

This is an integrated **mechanical browser smoke check**, not a business test pass, AI visual validation, assertion engine or complete MVP. Robot core → fixed custom Python keywords → HTTPX direct W3C WebDriver → ChromeDriver → Chrome for Testing. No model calls, customer credentials, customer URLs or legacy execution jobs. The new environment has nine pinned runtime distributions plus pip; no Selenium, Playwright, Puppeteer, SeleniumLibrary or Robot Browser. Existing UI regression tooling may still use its separate Playwright installation.

**Current stabilization verdict (2026-10-31): implemented, verification incomplete.** Real login/UI/API/TLS Mongo checks passed with an explicitly configured existing CfT installation. A separate fresh installation still failed all 10 headless and 5 headed first attempts after stabilization. Do not treat setup completion or the earlier cached-browser demo as clean-install readiness. See the [current evidence and blockers](../docs/mvp/M1A_DEVELOPMENT_SLICE.md#stabilization-and-real-development-verification-2026-10-31). A bounded Linux M1B experiment is now permitted under DECISIONS A14; Windows clean-install and Linux five-way reliability remain open.

## Setup

Windows x64 and Python 3.12 were tested. Use a trusted developer workstation, a non-production API environment and explicitly configured development Mongo/Redis for the existing app. No new worker or Redis consumer is needed. The API's existing dependency environment stays separate and unchanged. Browser/driver must be matching **full versions**; the runner checks the reported session browser version against ChromeDriver before navigating.

From repository root in PowerShell:

```powershell
# Installs only inside visual-runner/.venv and downloads pinned CfT binaries into ignored binaries/.
.\visual-runner\setup.ps1
# Validate a clean installation without replacing the working environment/binaries:
# .\visual-runner\setup.ps1 -Python 'C:\path\python312.exe' -InstallRoot 'F:\ai-qa-team\tmp\fresh-runner'
# If py -3.12 isn't available, pass an explicit Python 3.12 executable:
# .\visual-runner\setup.ps1 -Python 'C:\path\to\python.exe'
```

The reproduced bundle is 146.0.7680.31. The official CfT feed checked 2026-10-31 listed Stable 156.0.8078.80; the pin was deliberately not upgraded while diagnosing reproducibility. Setup now checks Python 3.12, downloads both bundles, invokes the bundled `setup.exe --configure-browser-in-directory` against only that CfT directory, waits for completion (Chromium success code 78), and verifies matching full versions. This sets required sandbox ACLs without installing/replacing normal Chrome. It does not disable the sandbox. The corrected fresh setup completed, but its browser smoke still failed. No automatic runtime download/upgrade occurs. Sources: [CfT feed](https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json), [sandbox configuration switch](https://chromium.googlesource.com/chromium/src/+/main/chrome/installer/setup/setup_constants.cc), [version selection](https://developer.chrome.com/docs/chromedriver/downloads/version-selection).

Set developer-owned settings in the **API terminal**, then start the existing API with its normal development environment. Paths are configuration only; HTTP clients cannot supply them. Do not put real secrets in arguments or copy production `.env` files.

```powershell
$env:FEATURES__VISUAL_RUNNER_LAB='true'
$env:APP_ENV='development'
$env:VISUAL_RUNNER_PYTHON='F:\ai-qa-team\visual-runner\.venv\Scripts\python.exe'
$env:VISUAL_RUNNER_CHROME='F:\ai-qa-team\visual-runner\binaries\146.0.7680.31\chrome-win64\chrome.exe'
$env:VISUAL_RUNNER_DRIVER='F:\ai-qa-team\visual-runner\binaries\146.0.7680.31\chromedriver-win64\chromedriver.exe'
$env:VISUAL_RUNNER_TIMEOUT_SECONDS='90' # validated range 15–120 seconds
Set-Location ai-qa-team-api
..\.feature-flags.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Adapt absolute paths to your checkout. `.feature-flags.venv` is the existing local API environment, not the new runner environment; alternatively use your established API interpreter. Startup performs the existing Mongo index initialization, so use explicitly configured development services. Keep `native_execution` and other legacy flags unchanged. Turning the new flag off denies every lab endpoint; active supervised runs receive cancellation. Restart to change environment flags.

In a separate UI terminal:

```powershell
Set-Location ai-qa-team-ui
$env:NEXT_PUBLIC_API_URL='/api'
$env:API_BACKEND_URL='http://127.0.0.1:8000'
npm run dev
```

Log in with a development account, open an authorized project, then **Visual Runner Lab** in the project sidebar (`/projects/{projectId}/visual-lab`). Start a headless check; separately select the visible-browser checkbox and start a new run. The page polls lifecycle/logs, shows three authorized screenshots, and permits cancellation. A fixed eight-second inspection window makes cancellation observable. The browser always opens the runner-owned synthetic sample on an ephemeral loopback port; there is intentionally no user-configurable target URL.

Fixture: synthetic name “Sample Tester”, quantity 3, Plus plan at $20, calculated total $60, scroll and confirm. Actions use fixed coordinates and keyboard events, not DOM selectors, script injection or vision. The sample itself uses ordinary JavaScript to render its form; the WebDriver client never executes arbitrary JavaScript. A completed protocol sequence displays **Browser smoke check completed**. The screenshot is evidence for developer inspection, not automatically evaluated business truth.

## API and persistence

- `POST /projects/{project_id}/visual-lab/runs` with only `{ "headed": false }` → 202.
- `GET .../runs` → latest ten project runs; `GET .../runs/{run_id}` → status.
- `POST .../runs/{run_id}/cancel` → request cancellation; poll to terminal.
- `GET .../runs/{run_id}/artifacts/{artifact_id}` → one of `01-open`, `02-filled`, `03-confirmed`, only if published for that run.

All operations require the default-off flag, development/local/test environment, authentication and active project membership. Cross-project run IDs return 404, including artifacts. UI gating is additional. Extra start fields are rejected; local filesystem paths, commands, keywords and URLs are never request inputs. APIs expose neither private configuration nor PID/path fields. Screenshots use private authenticated responses with no-store; there is no static file mount.

Mongo `visual_lab_runs` is additive history with explicit adapter `robot-direct-webdriver-smoke-v1` and mode `mechanical-smoke`. `visual_lab_locks` reserves one active browser per configured local host/database using atomic conditional upsert and the built-in `_id` unique index. No legacy `executions`, queue, response schema, subscription counter or AI usage changes. Runtime files in ignored `visual-runner/.runtime/{run_id}` are local scratch/IPC and artifacts; Mongo remains the durable run metadata source. They are not a cloud artifact store. Keep them private to the development OS account; no hostile-local-filesystem security claim. Multi-host routing/shared artifact storage is unsupported.

The supervisor holds an OS file lock until cleanup. ChromeDriver launches suspended, is assigned to a Windows kill-on-close Job Object, then resumes; Chrome descendants inherit that job. A heartbeat watchdog bounds parent-supervision loss; browser lifetime has a separate hard deadline. Normal cleanup closes the WebDriver session, closes the job and removes its profile. **No surviving browser/driver processes were observed in the tested cases.** That is evidence, not a guarantee for every forced termination; private scratch/profile remnants can remain. Cleanup observation uses bounded polling because process termination is asynchronous. No whole-job replay/retry exists.

Diagnostics expose only fixed startup stages (driver launch/readiness, session creation, browser launch, DevTools connection/handshake, version validation, timeouts, navigation), allowlisted reason/error codes and bounded numeric timings. Driver verbose output is consumed in memory and discarded; raw lines, full command lines and paths are not written to diagnostic records or returned. The child inherits an explicit OS-only environment including SystemDrive/AppData/ProgramData/ComSpec; API/database/provider secrets remain excluded. The session read timeout remains five seconds; no failed-session retry or timeout inflation was added. Readiness now requires both a live driver and protocol `ready=true` within its original six-second budget.

The API monitors to Mongo and releases its lease on exit. Restart recovery reconciles up to 100 prior active host-local records after 23 seconds, without relaunching them; status/list also reconciles. After API hard death, heartbeat expiry plus bounded teardown grace stops the browser (normally within ~14 seconds); stale records become interrupted on reconciliation. A second worker cannot take the Mongo lease until expiry, and the independent OS lock prevents overlapping browser creation even during recovery. This is development supervision, not production durable dispatch/outbox/fencing.

Artifacts are retained locally for development; automatic retention/deletion and remote storage are not implemented. Stop all lab runs before manually archiving/deleting local scratch. Do not delete lock/runtime files during active execution. Turning off the feature denies artifact reads too; it does not delete data. No customer uploads, arbitrary sites, production services or unrestricted browser execution are supported. Built-in sample CSP, fixed navigation, restrictive DNS and disabled browser background features reduce exposure. A mandatory local proxy accepts only the runner-owned sample origin and rejects external HTTP/metadata targets and all HTTPS tunnels; it never forwards arbitrary traffic. This is not a general OS egress firewall or a customer-execution security gate.

## Verification commands

From `visual-runner`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_runner.py -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe tests/browser_checks.py --chrome 'C:\path\chrome.exe' --driver 'C:\path\chromedriver.exe' --case headless
# Repeat --case headed, cancel, parent-loss, failure, driver-loss, timeout, kill-runner, duplicate.
```

The harness uses a synthetic sample and reports observed child process disappearance. `kill-runner` deliberately leaves its last IPC state active; the API reconciles a dead supervisor to interrupted. No test should interpret that last file snapshot as a running live browser. The `failure` case uses a missing browser path; it validates failure teardown, not an assertion failure.

From `ai-qa-team-api`, run `..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_lab.py -v`. The opt-in `test_visual_lab_browser.py` uses real runner processes with an in-memory Mongo protocol double; set `VISUAL_LAB_BROWSER_TESTS=1`, `LAB_TEST_CHROME` and `LAB_TEST_DRIVER` to synthetic local bundle paths before running that file. It does not connect to Mongo or Redis. Default discovery skips this integration check.

From `ai-qa-team-ui`, run `.\node_modules\.bin\tsc.cmd --noEmit --incremental false`. `tests/visual-lab.test.cjs` uses the existing external Playwright UI-test tooling and a separate Next server with `NEXT_PUBLIC_API_URL=http://feature-api.test`, port 3107. API calls/auth are synthetic intercepted fixtures. This tooling is **outside** the new runner environment.

Exact UI regression invocation (two terminals, from `ai-qa-team-ui`):

```powershell
# Terminal 1 — isolated intercepted-fixture server, not the real-service check
$env:NEXT_PUBLIC_API_URL='http://feature-api.test'
.\node_modules\.bin\next.cmd dev --webpack --hostname 127.0.0.1 --port 3107

# Terminal 2 — set an existing Playwright module directory and install/use Edge beforehand
$env:PLAYWRIGHT_MODULE_PATH='C:\path\to\node_modules\playwright'
$env:FEATURE_UI_URL='http://127.0.0.1:3107'
node --test tests/visual-lab.test.cjs
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
.\node_modules\.bin\eslint.cmd 'src/app/(app)/projects/[projectId]/visual-lab/page.tsx'
```

Sequential startup measurements, from `visual-runner` (no retries, all failures retained):

```powershell
$fresh='F:\ai-qa-team\tmp\fresh-runner'
& "$fresh\.venv\Scripts\python.exe" tests/startup_series.py --chrome "$fresh\binaries\146.0.7680.31\chrome-win64\chrome.exe" --driver "$fresh\binaries\146.0.7680.31\chromedriver-win64\chromedriver.exe" --headless 10 --headed 5 --output '../tmp/startup-series.json'
```

## Real development integration fixture

The opt-in fixture creates its own loopback TLS MongoDB data directory, CA/server certificate, synthetic normal-signup accounts, API process and Next server. It logs in through the real UI; there are no forged sessions, authentication overrides, route interceptions or Mongo doubles. It uses the existing normal local auth-cache fallback when no Redis runs at the fixture's unused port. Services use ports 27119 (Mongo), 8817 (API), 3317 (UI); occupied ports cause failure. No `.env` is read by the task API, no existing database/membership is used, and only processes started by the fixture are stopped. UI/backend source and normal authentication remain in use. Graceful restart is a task-local Uvicorn stop-file, not a new HTTP control route; interruption deliberately kills only that API.

Prerequisites: Windows x64, MongoDB executable at `C:\Program Files\mongodb\bin\mongod.exe`, Node at `C:\Program Files\nodejs\node.exe`, existing API packages, external Playwright/Edge, and the isolated runner. Optional `MONGO_TLS_CA_FILE` lets development use a private CA while preserving TLS validation and the existing certifi default; the fixture generates its own CA, never disables certificate checks.

From repository root:

```powershell
# Only if Uvicorn is absent from your existing API environment: install task-only tools
.\.feature-flags.venv\Scripts\python.exe -m pip install --target tmp/m1a-api-tools uvicorn==0.38.0

.\.feature-flags.venv\Scripts\python.exe ai-qa-team-api/tests/run_visual_lab_real_stack.py --install 'F:\ai-qa-team\tmp\fresh-runner' --api-tools 'F:\ai-qa-team\tmp\m1a-api-tools' --playwright 'C:\path\to\node_modules\playwright'
```

The default uses the fresh bundle and currently reproduces startup failures. The passing real integration evidence explicitly used `--chrome 'C:\Users\ram\.cache\puppeteer\chrome\win64-146.0.7680.31\chrome-win64\chrome.exe'`, an existing CfT binary, with the new isolated Python environment and matched driver. That is a declared comparison configuration, **not** an automatic fallback or dependency on Puppeteer. Do not substitute it silently for a clean-install result. This test-only override is not an HTTP input. Private task logs/certificates stay under ignored `tmp/m1a-real-*`; publish only the sanitized report/summary. The final observer command is `python ai-qa-team-api/tests/observe_visual_lab_fixture.py <task-fixture-directory>`.

See [M1A verification and M1B](../docs/mvp/M1A_DEVELOPMENT_SLICE.md) for actual results and remaining gates. Protocol references: [W3C WebDriver](https://www.w3.org/TR/webdriver2/), [Robot library API](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries).

## Resumed diagnosis checkpoint (2026-10-31)

Fresh-start failure remains unresolved: new separate probes failed 0/1 headless on the repository drive, 0/1 headless with the fresh payload relocated to Windows temporary storage, and 0/1 headed. Cached comparison completed 1/1. Four additional instrumented fresh session probes also timed out; these are distinct diagnostic attempts, not a full reliability series. All 308 common payload files matched by SHA-256. Six runner tests and pip check passed outside the tool sandbox; sandbox restrictions caused separate temporary-lock/socket errors. No startup behavior or dependency pin changed. See [resumed evidence and native-trace prerequisite](../docs/mvp/M1A_DEVELOPMENT_SLICE.md#resumed-startup-diagnosis-2026-10-31). Do not run the full 10/5 baseline or claim readiness as though a cause has been fixed; collect the narrowly scoped native trace first. M1B remains deferred.

## Startup diagnostic bundle

New Lab runs expose an expandable **Startup diagnostic bundle** in the existing project page. Restart the API with your established development command after updating code; the runner uses the updated Python files on its next launch. The Lab flag stays default off. Existing project authorization also covers these diagnostics; no new public debug endpoint or raw-log download exists.

The bundle includes driver version/state/exit code, browser state before and after cleanup, DevTools port-file existence, whether a session was created, fixed native error categories and stage timings. Missing observations remain unknown; no raw paths, commands, environment, IDs, port-file contents or driver/browser lines are published. Cleanup results are bounded observations, not universal guarantees. Historical records without diagnostics remain compatible. The runner explicitly selects CfT through `VISUAL_RUNNER_CHROME`; the user's normal Chrome may have a different version and is not used.

Current verification: two fresh headless attempts failed; one cached comparison completed. Both failed bundles showed Chrome and driver running, no DevTools file, no session; observed Chrome exited after cleanup. Eight runner tests, ten mocked Lab API tests, fourteen mocked feature/history tests, three intercepted UI tests, TypeScript, focused lint and pip check passed. No real-login/Mongo diagnostics rerun or full post-fix 10/5 baseline was performed. Root cause remains unresolved. See [diagnostic details/evidence](../docs/mvp/M1A_DEVELOPMENT_SLICE.md#bounded-startup-diagnostic-bundle-2026-10-31).

Exact focused commands (repository paths assume the existing fresh test installation):

```powershell
# From visual-runner:
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe -m unittest discover -s tests -p test_runner.py -v
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe -m pip check
# From ai-qa-team-api:
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_lab.py -v
```

The two-terminal UI fixture commands under Verification commands now run three tests; `FEATURE_UI_URL` must match the fixture server port. The diagnostic task used port 3109 instead of 3107. This is intercepted-fixture regression tooling, not a real-service verification.

## Session timeout clarification

Session creation now has a separate 45-second HTTPX read budget; other commands remain at five seconds. A fresh session succeeded in a diagnostic library trial after 24.4 seconds, but actual supervised verification still timed out at 45 seconds after reaching DevTools handshake. This is a partial timeout correction, not clean-install readiness. See the session timeout ownership experiment in docs/mvp/M1A_DEVELOPMENT_SLICE.md. The next hypothesis concerns renderer/page-target initialization after browser DevTools responds. Do not claim the previous five-second ReadTimeout was a Chrome crash.

Small factor comparison (2026-11-01): both filtered-environment library sessions succeeded with file and stderr-pipe driver logging (four session checks). A normal supervised fresh run created a session but failed during navigation; it is not a smoke success. No fix or full 10/5 baseline is established. Details and all attempts are recorded in M1A_DEVELOPMENT_SLICE.md under Environment and logging factors.

Robot diagnostics checkpoint (2026-11-01): fixed keywords now preserve sanitized failure codes even when Robot absorbs exceptions. Navigation confirmation and screenshot phases have distinct labels. Small supervised comparison: fresh 1/2 completed, cached 1/1; all three had no survivors observed after cleanup. The failed fresh attempt reports ReadTimeout during the coarse navigation phase. See the Robot failure capture and navigation comparison in M1A_DEVELOPMENT_SLICE.md. No full series or real-login/API/Mongo verification was rerun; variable browser latency remains unresolved.

Navigation budget checkpoint (2026-11-01): POST navigation now waits up to 12 seconds for the driver's ten-second page-load result; session creation is 45 seconds and ordinary commands remain five seconds. Two small actual smoke checks (fresh and cached) completed, and cancellation cleaned up. This corrects a deadline mismatch, not the unresolved variable browser startup delay. Newly copied cached files were also slower than the original in six direct probes, with path/volume confounding. See the File-state experiment and navigation deadline correction in M1A_DEVELOPMENT_SLICE.md. No full 10/5 baseline or security bypass was performed.

Same-volume checkpoint (2026-11-01): an original cached CfT and a new task copy on C were probed in order original/copy/copy/original, producing DevTools files after 2.468/12.594/0.797/2.671 seconds. This supports cold path/file state as a hypothesis, not an antivirus diagnosis or verified fix. Use `file_state_diagnostic.py --cached <original directory> --fresh <fresh directory> --copy-root <task parent on C> --pair-only` for the bounded diagnostic; each profile is unique and normal execution is unchanged. See Same-volume cached-copy comparison in M1A_DEVELOPMENT_SLICE.md. No full baseline was run.

## Stable 156 upgrade experiment (2026-11-02)

Official Stable 156.0.8078.80 was downloaded with a matching win64 driver into `tmp/m1a-cft156-experiment` using setup.ps1 -Version/-InstallRoot. Full setup/version/dependency checks passed; resumed runner suite: ten passed. Actual headless and headed smoke attempts both failed during session handshake (0/1 each); the old 146 headless control completed 1/1. No default pin, normal Chrome or API environment changed. This is not a verified upgrade or a startup fix. Details, exact isolated setup command and all attempts are under Matched stable 156 experiment in M1A_DEVELOPMENT_SLICE.md. Native tracing remains unperformed because the needed tracing tool/session is unavailable.

Profile-location checkpoint (2026-11-02): a diagnostic-only F/C/C/F comparison completed all four fresh-browser Robot workflows (25.110/15.719/14.516/15.407 seconds), each with three screenshots and no survivors observed. The final F result matches C closely, so moving profiles is not an established fix and the normal configuration was preserved. See Isolated profile-location comparison in M1A_DEVELOPMENT_SLICE.md. Developer reproducer: isolated runner Python → tests/profile_location_diagnostic.py --chrome <controlled CfT executable> --driver <matched driver>. No full baseline or M1B was run.

## Isolated Linux image spike (2026-11-02)

See [Linux image setup and verification gate](linux/README.md). A separate non-root
Linux/amd64 Dockerfile and fixed headless launcher reuse the existing Robot/sample/
HTTPX workflow. Windows keeps its Job Object default; no UI/API dispatch changes.
The runtime network is disabled except loopback; no browser sandbox bypass is added.
Image build and Linux execution are NOT RUN: Docker/Podman are absent and WSL has
no installed distributions. Three new mocked dependency/process tests and ten
existing runner tests passed (the latter outside the restricted tool sandbox).
Windows latency remains unresolved. No cloud deployment or M1B occurred.


Linux results update (2026-11-02): user built image/manual smoke/cancellation;
agent real-container baseline 3/3 completed, forced-stop and diagnostic timeout
exited as expected. Five containers exited/PID zero/no OOM. Per-browser telemetry
unavailable, forced-kill reconciliation absent. Earlier build-unavailable notes
are historical; see [current Linux evidence and commands](linux/README.md).


Linux guard update (2026-11-02): separate :guard image adds explicit local stopped-
container reconciliation and evidence-preserving child/outer-timeout finalization.
Real forced-stop, unchanged 100s+10s outer-watchdog fault injection and completed-
record preservation each passed once; eight focused unit tests passed. See
[Linux guard instructions](linux/README.md). No automatic or multi-host reconciler,
API dispatch, cloud deployment or M1B is implemented by this change.


Batch UI update (2026-11-02): existing project Visual Runner Lab offers synthetic
batch start/status/cancel/evidence under both flags; no customer URLs. API/runner
runtime is unchanged in this UI task. The contract exporter now also generates
TypeScript. See [UI setup, regression commands and limitations](../docs/mvp/EXECUTION_CONTRACTS.md#batch-ui-verification-and-operation-2026-11-02).
Nine distinct intercepted UI checks passed; normal-login full-stack batch execution
was not rerun. Prior real backend evidence stays separate. Flags remain default off.


Linux per-check pool revision (2026-11-02): the existing Lab can group checks into
batches while the API schedules one isolated Linux container per check. The shared
development pool defaults to five; set VISUAL_BATCH_GLOBAL_SLOTS,
VISUAL_BATCH_ACCOUNT_SLOTS and VISUAL_BATCH_PROJECT_SLOTS explicitly when testing.
Reuse the pinned :batch image; no runner dependency change/rebuild is needed.
See [contracts/setup](../docs/mvp/EXECUTION_CONTRACTS.md) and
[actual qualification](../docs/mvp/M1A_DEVELOPMENT_SLICE.md). Five-way verification
is incomplete (0/5 first-attempt startup completions; separate control engine
failure). Do not treat configured capacity or passing unit tests as readiness.


Preparation update (2026-11-03): View evidence -> Container preparation now shows
server-owned stages, first error and timings. Restart the development API and reload
the UI; no runner image rebuild or dependency change. Two isolated one-case controls
completed, and five preparations succeeded; five-case workflow completion was 4/5
with one later session-not-created response. Historical preparation cause remains
unknown. See M1A/EXECUTION_CONTRACTS for real-vs-double evidence, fault injection,
cancellation and qualification limits. No automatic retry or M1B.


Current planning boundary (2026-11-03): the accepted Linux M1B experiment starts
with screenshot-derived targeting of one visible synthetic button, followed by
bounded waits/scrolling, independent assertions, selective retained evidence and
latency/usage controls. See MVP_SPEC/IMPLEMENTATION_PLAN and DECISIONS A14. Five
Linux check slots remain the MVP/default capacity; this documentation amendment
changes no runtime setting or dependency and does not qualify five-way reliability.
## BrowserStack visual button experiment

The separate BrowserStack experiment uses one remote session and at most one
OpenAI image request to locate a visible button on a fixed synthetic page.
The fixture varies the button position. The probe requires a unique proposal,
maps normalized coordinates to screenshot pixels, and rejects coordinates outside
the known synthetic button bounds. It compares the current URL and screenshot
immediately before clicking once. A synthetic title change confirms the click
reached the button. It keeps one screenshot on confirmation, target rejection,
or an unconfirmed click. This is a mechanical experiment
outside the application gateway, project APIs, and Linux container qualification.

From `visual-runner`, with the runner virtual environment activated, set
`BROWSERSTACK_USERNAME`, `BROWSERSTACK_ACCESS_KEY`, `OPENAI_API_KEY` and an existing
directory in `RUNNER_TEMP` through your environment or secret store, then run:

```powershell
python -c 'from linux.browserstack_probe import main; main(visual=True)'
python -m unittest discover -s tests -p test_visual_button_probe.py -v
```

On the smoke branch, a push that changes `browserstack-probe.yml` and includes
`[visual-button]` in its tip commit message selects the visual experiment.
The manual Actions workflow also has a `visual_button` input. GitHub requires a
manually dispatched workflow to exist on the default branch. Configure the
three named credentials as Actions secrets before dispatching. The regular
push-triggered BrowserStack form probe does not use the OpenAI secret.
The guard tests use doubles and make no model or BrowserStack calls.
