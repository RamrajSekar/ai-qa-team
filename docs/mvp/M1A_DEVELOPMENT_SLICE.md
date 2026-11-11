# M1A integrated development slice

**Current verdict: M1A implemented but verification incomplete.** The [stabilization results below](#stabilization-and-real-development-verification-2026-10-31) supersede the previous task's verification claims. Real login/UI/API/Mongo passed with the explicitly configured cached CfT installation; fresh-install startup remains a release blocker. Do not start M1B yet.

Implemented 2026-10-31 on `dev`, baseline `2479de4017cd8e29516daa1ecf62d5763bc2b6b2`, uncommitted. Existing user edits to AGENTS/skill/context/docs and deleted historical progress files were present before this task and preserved. This document records implementation evidence; the earlier gap analysis remains the historical assessment.

## Delivered boundary

Existing project UI → FastAPI member authorization/feature guard → additive Mongo run metadata/local singleton lease → separate Python supervisor process → Robot core → fixed custom library → HTTPX direct WebDriver → ChromeDriver → matched Chrome for Testing. Server-owned loopback sample has synthetic name/quantity/dropdown/calculated total/confirmation. Fixture coordinates/keys and three screenshots only; no visual AI, selectors, model calls, customer credentials, arbitrary URLs, uploaded Robot programs or business assertions.

New default-off Pydantic `visual_runner_lab` gate, plus development/local/test environment check. It neither enables nor depends on `native_execution`. Every start/list/status/cancel/artifact route checks project membership. Explicit adapter `robot-direct-webdriver-smoke-v1`, mode `mechanical-smoke`, states starting/running/stopping/completed/failed/cancelled/interrupted/timed_out; there is deliberately no business verdict or passed status. Success text is **Browser smoke check completed**.

Reusable components: existing auth dependency/project membership, feature policy and UI feature provider, Next project navigation/layout/API fetch, Mongo async persistence. New modules: `app/models/visual_lab_model.py`, `app/routes/visual_lab_routes.py`, `app/services/visual_lab_service.py`; isolated `visual-runner/lab/{runtime,sample,webdriver,keywords,supervisor}.py`; project `visual-lab/page.tsx`. Existing execution models/routes/worker/history/Redis and application dependency files remain unchanged. Only new runner requirements are installed separately.

Mongo `visual_lab_runs` and `visual_lab_locks` are additive; no migration or old-record rewrite. The lock uses Mongo's built-in unique `_id` and conditional lease upsert, with an independent kernel file lock until runner teardown. A Windows Job Object owns suspended-then-resumed ChromeDriver and browser descendants. Parent heartbeat loss, bounded runtime, cancellation, normal exceptions and forced supervisor death close that process tree. API shutdown requests cancellation; delayed startup/status reconciliation records interrupted or final state without replay. No legacy consumers see the new runs. Logs/codes and artifact identifiers are allowlisted; APIs do not expose process arguments, configuration paths or arbitrary files. Child environment excludes API/database/AI credentials.

The sample origin is created by the supervisor, not supplied by customers or copied from an environment URL. It serves no external resources and has restrictive CSP. Chrome uses a fresh profile, disabled background features, restrictive DNS resolution and a mandatory local proxy that accepts only the sample origin and refuses external HTTP targets/HTTPS tunnels (including metadata addresses). No arbitrary traffic is forwarded. This controlled-app restriction is not a general OS egress firewall. Windows local development only; no WSL/GCP, arbitrary-site or customer-security readiness claim.

## Historical M1A verification — previous implementation task

Windows Python 3.12.14, Robot 7.5, HTTPX 0.28.1, Chrome for Testing/ChromeDriver **146.0.7680.31**, checked matching full versions. Existing cached CfT binary was used; matched driver was downloaded into ignored runner binaries. Full nine-package runtime graph was installed into a fresh separate venv; exact installed-distribution allowlist excludes all prohibited clients. Setup script downloads both binaries for a reproducible chosen version; its full download-both path was not rerun because CfT already existed locally.

| Check | Actual result |
| --- | --- |
| New isolated API authorization/service suite, `test_visual_lab.py` | 8 passed; project/feature/production rejection, fixed input validation, scoped run lookup, private screenshot response, duplicate lease launch rejection and interrupted-state/diagnostic filtering. |
| Opt-in `test_visual_lab_browser.py` | Passed through actual HTTP routes/service/isolated runner and real Chrome, using synthetic identity/membership and an in-memory Mongo protocol double. Start → screenshot/status → cancel → terminal; second run completed with three screenshots; new service instance read persisted fixture metadata. Cross-project duplicate start rejected and other-project screenshot denied. |
| Isolated runner `test_runner.py` | 5 passed: exact installed graph, kernel lock exclusion/release, selector/script-free actions protocol, fixed four-keyword interface, sample proxy external HTTP/metadata/tunnel rejection. `pip check` passed. |
| Real headless and headed harness cases | Each completed separately with three PNGs. Final screenshot manually inspected: “Confirmed: Sample Tester / $60”. This inspection is not an implemented assertion evaluator. |
| Real cancellation and parent-heartbeat-loss cases | Cancelled/interrupted respectively; observed driver/browser processes disappeared. |
| Real missing-browser failure, driver loss after session startup and runtime timeout | Failed/failed/timed_out respectively, with bounded cleanup. Driver-loss check verified no surviving profile/driver processes. These are infrastructure cases, not business assertion failures. |
| Hard-killed runner and concurrent second runner | Job Object removed observed browser/driver processes after hard kill; last IPC file remained running until backend reconciliation by design. Concurrent runner failed without opening another browser; first completed. |
| Existing `test_feature_flags.py` | **13 passed**, including disabled worker no-consumption and execution/history ownership compatibility. Previously stalled suite completed outside the sandbox. No legacy behavior changes were needed. |
| UI `tsc --noEmit --incremental false` | Passed. |
| Focused ESLint on lab page | Passed after using an unoptimized authenticated blob image via Next Image. |
| UI `node --test tests/visual-lab.test.cjs` | 2 passed against isolated Next server with intercepted synthetic API: start/observe/cancel, separate visible selection, completion wording, protected PNG rendering, feature-off route prevents lab fetch/mount. No page runtime errors. |
| Scope/whitespace review | `git diff --check` and explicit new-file whitespace scan; only scoped additions/edits alongside preserved initial user changes. No commit/push/deployment. |

Commands and Windows setup are in [visual-runner/README.md](../../visual-runner/README.md). UI browser regression tooling uses existing external Playwright outside the runner graph. Tests did not use production, real account secrets, Mongo/Redis services or AI. The HTTP integration double validates application lifecycle/query behavior but cannot certify live Mongo atomicity, durability, indexes, network or restart behavior. Do not describe synthetic auth fixtures as a live login verification.

Initial restricted-sandbox venv setup hit a temporary-directory permission issue and driver download hit restricted DNS; workspace temp and approved local dependency/download execution resolved them. API async tests initially stalled in the sandbox but passed outside it; the same observation resolved the historical feature-suite stall without an application fix. Initial and one repeat browser startup failed before screenshots with a WebDriver command error; another HTTP integration repeat passed, as did five consecutive reduced-environment direct startup probes. Root cause is unresolved: this is an intermittent local startup limitation, not a claimed fix. No automatic browser retry was added. Safe session-specific error codes are now recorded. A first driver-loss harness attempt inspected processes too slowly and missed the live driver; immediate PID-targeted termination corrected the harness and the failure/cleanup check passed.

Installed wheel license metadata was inspected separately: Robot Apache-2.0; HTTPX/httpcore/idna BSD-3-Clause; anyio/h11 MIT; certifi MPL-2.0; sniffio MIT OR Apache-2.0; typing_extensions PSF-2.0; bootstrap pip MIT. Wheel notices remain in the isolated environment; browser/native redistribution and full third-party notice packaging are later release work. PowerShell setup script syntax parsed successfully; no application lockfiles were regenerated.

Remaining limitations: local one-host development service; no durable production outbox/fencing, remote artifact storage/retention or general network firewall; no business assertion evaluator, visual target model or AI usage accounting; no production secret remediation; no real Mongo/live-login deployment check; no WSL/Linux/GCP validation. Local scratch/profile remnants may remain after force kill; no orphan browser processes were observed in forced-kill checks. Recent-list shows ten runs, recovery sweep handles up to 100 active local records; larger-scale administration is out of scope.

## Bounded M1B follow-up — deferred pending stabilization

Estimated **2–4 engineer-weeks** at 35 focused hours/week for an experienced engineer, subject to vision reliability; not a commitment to the full M1/pilot. Keep the same controlled sample and Windows process boundary, one browser and default-off gating. Do not expand to customer apps, media learning, cloud, arbitrary specs or legacy execution migration.

1. Define a versioned, server-owned structured spec with required independent text/numeric assertions and explicit expected values. Keep lifecycle separate from an assertion-based verdict; mechanical completion must never become Passed by inference. Persist exact spec/model/prompt/observation identity.
2. Extend existing AIUsageService → LLMGateway/provider boundary with validated screenshot input and a dedicated bounded operation; no model SDK/key inside the runner. Project authorization and redacted observations precede invocation. Count image/model calls/latency/token usage and enforce server-owned per-run plus account/daily spend controls; missing cost is not zero. Enforce no silent provider/account fallback and no AI when flag/capability/budget fails.
3. Replace fixture coordinates with schema-bound target proposals tied to fresh screenshot dimensions/identity. Trusted dispatcher enforces coordinate bounds, supported action and remaining budget. Handle ambiguous target by bounded reacquisition or Needs review, never DOM/selector/script fallback. Fixed sample origin/action surface stays unchanged.
4. Evaluate approved text/numeric assertions independently from navigation/action completion, using reliable observations and deterministic comparisons where possible. Include deliberately wrong expected total, missing required assertion, ambiguous OCR/vision, model/provider failure and insufficient budget. Expected/observed/inferred/unknown stay distinct.
5. Add regression corpus and denominator-based repeat measurements: successful flow, wrong expectation, duplicate/unknown target, stale screenshot, cancellation during model work, timeout after submit and no blind retry. Verify zero unsupported actions, every required assertion accounted for, secret-free telemetry, bounded cost and all cleanup checks. Show explicit uncertainty instead of invented confidence thresholds.

Acceptance gate: controlled application only; real screenshot target identification demonstrated without prohibited clients; reliable positive/negative assertion outcomes; ambiguous evidence surfaced; usage caps enforced and auditable; M1A authorization/cleanup/history regressions pass. After that, explicitly scope the early WSL/Linux/GCP feasibility spike. A deployment task remains separately authorized.

## Stabilization and real development verification 2026-10-31

Branch `dev`, baseline commit `2479de4017cd8e29516daa1ecf62d5763bc2b6b2`, uncommitted working tree. Prior M1A code and user guidance/documentation edits/deleted progress files were present at entry and preserved. This section records checks actually performed in the stabilization task; the preceding section is historical. No production services, customer sites/data, AI calls, cloud deployment, commit or push.

### Findings and bounded changes

- **Startup failure reproduced and staged:** driver version detection, launch and protocol readiness succeed. Fresh CfT stalls after `browser_launch` during WebDriver session creation and hits the unchanged five-second HTTP read timeout. It does not reach navigation. Raw driver output is consumed in memory and reduced to allowlisted stage codes; no raw command lines/paths/browser output are recorded. Browser/driver versions match. Chrome executable and chrome.dll hashes match the working cached release, but this does not prove all installation state is equivalent. Port allocation was examined; no failure was attributed to driver port binding/readiness. **The remaining fresh-install root cause is not established.**
- **Readiness bug fixed:** HTTP 200 alone previously passed readiness. It now requires `value.ready=true`, a live driver, a six-second monotonic budget and bounded individual probes. A deterministic protocol test exercises false→true and dead-driver cases. This is a demonstrated defect, not proof it caused every historical startup failure.
- **Windows environment corrected:** the API child now preserves standard OS context (SystemDrive, AppData, ProgramData, ComSpec and program directories) while excluding database/JWT/provider secrets. Before this correction a real cached-browser run failed at DevTools connection; afterward the full real integration passed. Standalone harnesses use the same OS-only contract. A canary test checks secret exclusion. Do not claim this fixes the separate fresh-install problem.
- **Fresh setup corrected:** Python 3.12 is checked; an explicit `-InstallRoot` preserves working installations. Both downloads/extractions and full-version checks execute. The unpacked CfT directory lacked sandbox capability ACLs present in the cached installation; setup now invokes the bundled directory-only configuration switch and waits for Chromium success status 78. It does not install normal Chrome or disable sandboxing. Fresh startup still fails after this correction.
- **Measurements corrected:** process termination can be asynchronous. Startup-series cleanup observation polls boundedly before another browser can launch; failed attempts remain in the denominator. An initial immediate sample saw one process and stopped the series; a later observation found none. That original unverified sample remains in diagnostic evidence. No whole-run/session retry, security relaxation, arbitrary startup delay or timeout inflation was added. A diagnostic pipe-transport experiment also failed and was reverted.
- **Real development support:** optional `MONGO_TLS_CA_FILE` supplies the task-owned Mongo CA while preserving TLS validation and the existing certifi default. Separate CA/server certificates, normal authentication and actual Mongo are used by opt-in fixture tooling. No authentication or database overrides/mocks are used by that fixture. Graceful restart control is local test-process IPC, not an application endpoint.

Application changes are limited to `app/services/visual_lab_service.py`, `app/models/visual_lab_model.py`, the Lab page's stage display, and optional Mongo CA configuration/connection. Runner changes are in `lab/webdriver.py`, `lab/runtime.py`, `lab/supervisor.py`, `setup.ps1` and the verification harnesses/tests. New real-stack tooling lives under API tests and `ui/tests/visual-lab.real.cjs`. Legacy execution/history/queues, feature defaults, application dependency environments and lockfiles remain unchanged. M1B functionality was not implemented.

### Startup baseline: first attempts, no concurrent runner browsers

All rows below use Chrome/ChromeDriver 146.0.7680.31. Durations are whole supervisor lifetimes (including failed-start cleanup, or the fixed inspection window on completed runs), not just browser-launch latency. Per-stage timings and every run ID/outcome are retained in JSON.

| Configuration / cohort | Headless first-attempt success | Headed first-attempt success | Observation |
| --- | --- | --- | --- |
| Initial unconfigured fresh bundle, full requested series | **0/10** | **0/5** | All ReadTimeout after browser launch. [Every attempt](evidence/startup-before-stabilization.json). |
| Corrected fresh setup + OS-only environment, final requested series | **0/10** | **0/5** | All ReadTimeout after browser launch; no navigation. Headless 6.609–8.328 s; headed 6.703–8.406 s. No survivors observed after bounded cleanup in all 15. [Every attempt](evidence/startup-after-stabilization.json). |
| Earlier current-task diagnostic series, existing cached CfT | **3/3** | Not attempted in that series | Positive comparison only, not clean-install evidence. |
| Other current-task one-off diagnostic probes | Recorded individually | N/A | Includes failures from original fresh attempt, stage probe, pipe experiment, C-drive copy and sandbox-configured probe, plus a successful cached-payload comparison. [Unedited denominators/results](evidence/startup-diagnostic-probes.json). |

The two 15-run cohorts are separate configurations; neither is omitted or merged into a misleading success percentage. The cached real-service workflow below is also a distinct cohort. These counts are development observations, not statistical reliability proof.

### Fresh Windows installation

Two empty task directories were used (`tmp/m1a-clean-install`, then corrected `tmp/m1a-clean-fixed-install`), without deleting/replacing `visual-runner/.venv`, working binaries, normal Chrome or the API environment. The corrected `setup.ps1` completed all steps. Python **3.12.14**, bootstrap pip **25.0.1**, Robot **7.5**, HTTPX **0.28.1**. Runtime graph: anyio 4.11.0, certifi 2025.10.5, h11 0.16.0, httpcore 1.0.9, idna 3.11, sniffio 1.3.1, typing_extensions 4.15.0. `pip check` and exact distribution allowlist passed; no Selenium/Playwright/Puppeteer/SeleniumLibrary/Robot Browser distribution appears directly or transitively.

**Download/extraction/dependency/version verification passed; fresh smoke execution failed.** Those are separate results. The official [CfT feed](https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json), checked 2026-10-31, listed Stable **156.0.8078.80** (feed timestamp 2026-10-30). The historical 146.0.7680.31 pin was reproduced, not upgraded or represented as a currently supported secure release. The [Chromium directory configuration implementation](https://chromium.googlesource.com/chromium/src/+/main/chrome/installer/setup/setup_constants.cc) and [installer status definitions](https://chromium.googlesource.com/chromium/src/+/main/chrome/installer/util/util_constants.h) document the sandbox configuration step/code. Reading public installer implementations does not introduce those tools' client libraries into the runner.

### Verification table: real services versus fixtures

Real stack: Windows, MongoDB **8.2.1** on loopback 27119 with validated task-owned TLS CA, FastAPI through Uvicorn **0.38.0**, Next **16.1.6** on 3317, external UI Playwright **1.62.1**/Edge. The existing API environment lacked Uvicorn, so it was installed into `tmp/m1a-api-tools` only (click 8.5.0/h11 0.16.0); existing site-packages were not altered. The task API starts outside repository `.env` lookup with explicit non-production settings. Normal existing local auth-cache fallback was used, not a Redis mock or a new execution consumer. API startup index creation touched only this dedicated database.

| Check | Environment | Actual result / evidence |
| --- | --- | --- |
| Normal signup → real UI login → authorized project | Real UI/API/TLS Mongo, synthetic accounts | PASS. Signup uses normal endpoint; cookies are cleared and UI email/password login must succeed. No forged cookies/auth overrides. Project created through normal authorized API and opened in real UI. |
| Headless completion / three PNGs and a separate headed completion | Real stack, **explicit cached CfT comparison configuration** | PASS. Both actual Robot/direct-WebDriver runs completed; three PNGs fetched and rendered. Success label remained “Browser smoke check completed”. Fresh bundle is **not** certified by this pass. |
| UI cancel; refresh/history | Same real stack | PASS. Running check cancelled; page refresh retained persisted completed history. |
| API restart preserves completed metadata/artifact access | Same real Mongo process, task-owned API gracefully restarted | PASS. No replay or session forgery. This is not a Mongo-server restart, production durability or multi-host test. |
| Duplicate/concurrent starts and later valid run | Actual Mongo conditional upsert and normal service path | PASS: one 202/one 409; only one extra run record. After interruption a later start was accepted and cancelled. No misleading duplicate active record remained. |
| Hard API interruption, cleanup/reconciliation without replay | Task-owned API only | PASS. Heartbeat loss led to interrupted state; service restart reconciled old run and lease recovered. |
| Nonmember cannot list/read/cancel/fetch another project's PNG | Second normal signup/UI login; no customer memberships changed | PASS: four real 404 denials, including an existing completed screenshot. |
| Feature-off operations and active run | Real stack, graceful task API restart with flag off | PASS: start/status/cancel/artifact requests rejected 403; active run cancelled during normal shutdown. Re-enable did not replay it. |
| Final actual Mongo / process/log observation | Real fixture | **7 run records, 0 active, 0 held leases**. No remaining profile processes observed for all seven IDs; no JWT-shaped value or cookie-dump marker found in the task API log. This scan is not a general secret-leak audit. [Summary](evidence/real-mongo-summary.json), [observation](evidence/real-cleanup-and-log-scan.json). |
| Lab authorization/service tests | Mocked isolated API | **9 passed**, including disabled/production guards, project scope, artifact allowlist, lease launch rejection, diagnostic filtering and OS-only secret-free environment. |
| Runner graph/protocol/lock/proxy/readiness tests | Fresh isolated venv, protocol fixtures/local proxy | **6 passed**, `pip check` passed. |
| Cancel, driver loss, timeout, forced supervisor kill, parent loss, duplicate | Real cached CfT + fresh Python/driver, controlled local sample | All six harness cases reached expected outcomes; no surviving browser/driver processes observed. Forced-kill IPC snapshot can remain running until API reconciliation; it is not proof of a live process. |
| Existing feature/history compatibility suite | Mocked isolated API, rerun in this task | **13 passed**. No new jobs went to legacy consumers. |
| UI tests | Intercepted synthetic API, distinct from real-service tests | **2 passed**; start/observe/cancel/mode/screenshot rendering and feature-off mounting. |
| TypeScript, focused lint, syntax/whitespace | Static checks | Passed; exact commands below and in README. |

[Passing real-service report](evidence/real-integration-passed.json) contains all ten successful scenario results and durations. [Earlier failed real attempts](evidence/real-integration-failed-attempts.json) retain the fresh-browser failure and cached-browser failure before OS context correction. Initial infrastructure starts that failed for missing Uvicorn and a certificate-fixture mistake were corrected; they are not successful browser attempts. Actual real checks used the corrected isolated infrastructure and normal auth.

### Reproduction commands

From repository root, with an existing Python 3.12 API interpreter and Node/Edge/Mongo prerequisites:

```powershell
.\visual-runner\setup.ps1 -Python 'F:\ai-qa-team\.feature-flags.venv\Scripts\python.exe' -InstallRoot 'F:\ai-qa-team\tmp\m1a-clean-fixed-install'
.\.feature-flags.venv\Scripts\python.exe -m pip install --target tmp/m1a-api-tools uvicorn==0.38.0
# Known passing comparison configuration, explicitly selected; no automatic fallback:
.\.feature-flags.venv\Scripts\python.exe ai-qa-team-api/tests/run_visual_lab_real_stack.py --install 'F:\ai-qa-team\tmp\m1a-clean-fixed-install' --api-tools 'F:\ai-qa-team\tmp\m1a-api-tools' --chrome 'C:\Users\ram\.cache\puppeteer\chrome\win64-146.0.7680.31\chrome-win64\chrome.exe' --playwright 'C:\Users\ram\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
# Omit --chrome to reproduce the fresh-install blocker; do not call that a passing clean-install check.
```

From `visual-runner`:

```powershell
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe tests/startup_series.py --chrome 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chrome-win64\chrome.exe' --driver 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chromedriver-win64\chromedriver.exe' --headless 10 --headed 5 --output '../tmp/m1a-postfix-startup-series.json'
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe -m unittest discover -s tests -p test_runner.py -v
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe -m pip check
foreach ($case in @('cancel','driver-loss','timeout','kill-runner','parent-loss','duplicate')) {
  ..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe tests/browser_checks.py --chrome 'C:\Users\ram\.cache\puppeteer\chrome\win64-146.0.7680.31\chrome-win64\chrome.exe' --driver 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chromedriver-win64\chromedriver.exe' --case $case
  if ($LASTEXITCODE -ne 0) { throw "Fixture failed: $case" }
}
```

From API: `..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_lab.py -v`, then the same command with `-p test_feature_flags.py`. From UI: TypeScript/lint and the exact two-terminal intercepted regression commands in [README](../../visual-runner/README.md#verification-commands). Final root check: `git diff --check`. Do not run the real-stack fixture while another runner series is active; it fails occupied ports instead of stopping other processes.

### Remaining blockers and next action

**M1A implemented but verification incomplete:** clean installation cannot yet execute the smoke, despite matching binaries, sandbox ACL setup, isolated dependencies and fixed OS context. No successful fresh-install smoke or supported-current-release validation is claimed. Do not recommend/start M1B on the cached-browser success alone.

Next bounded task is native Windows startup diagnosis comparing fresh versus cached installation with the same matched pair, context and Job Object. Capture restricted Process Monitor/ETW evidence for that task-owned browser's launch/DevTools initialization and investigate the remaining installation/ACL/runtime difference; do not disable sandbox/Job Object, add retries, copy machine caches as a fix, or increase timeouts without a demonstrated cause. Fix that cause, then repeat the 10/5 first-attempt baseline and the **real stack using the fresh bundle**, preserving failures. Selecting a current supported CfT pin is a separate explicit compatibility decision; both versions/results must remain recorded if changed.

No WSL/Linux, cloud, production durability, multi-host routing, exactly-once execution, customer-app security, visual AI or business assertion readiness was tested or claimed. Automatic retention/native redistribution notices remain future release work. All task-owned services were stopped; prior user processes/data were not targeted.

## Resumed startup diagnosis (2026-10-31)

This is new evidence from the current uncommitted `dev` checkout, not a rerun of the earlier full 10/5 series or real UI/API/Mongo integration. Prior user changes and the project-overview fixes are preserved. No M1B, application/runner behavior change, dependency upgrade, production access or deployment occurred.

| Configuration | First-attempt completion | Duration | Failure stage / cleanup |
| --- | --- | --- | --- |
| Existing fresh bundle on repository drive, headless | 0/1 | 11.141 s | Session creation after browser launch; ReadTimeout. No survivors observed. |
| Existing cached comparison, headless | 1/1 | 20.766 s | Completed with three screenshots; no survivors observed. |
| Fresh payload copied into a new task-owned Windows temporary directory and directory sandbox configured, headless | 0/1 | 7.828 s | Same ReadTimeout; no survivors observed. No cached state copied. |
| Existing fresh bundle on repository drive, separate headed session | 0/1 | 6.516 s | Same ReadTimeout; no survivors observed. |
| Additional instrumented fresh headless native probes | 0/4 session creations | Not measured as a timing series | ReadTimeout in each; no per-probe cleanup observation. Final runner-profile process check found no surviving Chrome/ChromeDriver. These were diagnostics, not full Robot workflow completions. |

All attempts were sequential. Durations are whole supervisor lifetimes, not browser launch latency. Failures remain in their separate denominators. [Sanitized evidence](evidence/startup-resumed-diagnosis.json) preserves the four ordinary harness run IDs/stages/timings. One earlier sandboxed probe from the connectivity follow-up failed driver readiness with unverified cleanup; it is a distinct environment and was not included in these outside-sandbox cohorts. Its later permitted process check observed no survivors.

SHA-256 comparison found **all 308 common browser payload files identical**; the cached directory additionally contains four files under a literal SystemDrive cache directory. Those files were not copied as a fix. Both browser executable streams had only normal file data. The native probes enabled stderr diagnostics temporarily and emitted only allowlisted stage/error metadata, module names and thread summaries; raw driver/browser lines, command lines, paths and lock names were not published. The fresh process sample showed four threads, early loader modules including chrome_elf, and no loaded chrome.dll at that instant. Wait-chain inspection identified no blocking dependency. These samples narrow the stage but do not establish an ACL, antivirus, loader or Chrome defect.

**Root cause remains unresolved.** Driver readiness and matched version checks are not the failing stage outside the tool sandbox. The failure also reproduces outside the repository drive. Process Monitor/native debugger was not installed and the execution token was not an elevated administrator, so a scoped native filesystem/registry/image-load trace could not be collected here. No automatic retry, sleep, longer timeout, sandbox/Job Object bypass, cache-state substitution or pin upgrade was introduced.

Runner verification from `visual-runner`: six tests passed outside the tool sandbox; `pip check` passed. The initial command from repository root failed to import `lab`, then was corrected to the documented working directory. The sandboxed suite produced two environmental errors (temporary-file lock permissions and forbidden loopback sockets); neither is represented as an application defect or a passing test. No real UI/API/Mongo/login checks, clean downloads, full 10/5 series, supported-release validation or cloud checks were rerun in this investigation.

Reproduce the fresh one-shot probe from repository root in a normal developer PowerShell terminal:

```powershell
Set-Location F:\ai-qa-team\visual-runner
..\tmp\m1a-clean-fixed-install\.venv\Scripts\python.exe tests/startup_series.py --chrome 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chrome-win64\chrome.exe' --driver 'F:\ai-qa-team\tmp\m1a-clean-fixed-install\binaries\146.0.7680.31\chromedriver-win64\chromedriver.exe' --headless 1 --headed 0 --output '../tmp/m1a-manual-fresh-probe.json'
```

Next action requires an elevated, narrowly filtered native trace of that task-owned fresh launch and a cached comparison. Use official Microsoft Process Monitor with capture initially stopped, a filter restricted to the exact task CfT executable path, and drop filtered events enabled before capture. Avoid unrelated user Chrome processes; retain raw PML locally and privately because it can contain command lines, registry data and paths. Stop capture immediately after the bounded probe; inspect image-load/file/registry failures and blocked thread stacks. Share only a sanitized finding, not raw trace contents. Obtain diagnostic access before tracing; do not disable endpoint protection or browser security. A path-filtered trace may omit a relevant helper, which can be added only after identifying it as task-owned.

M1A remains **implemented but verification incomplete**. After identifying and fixing a demonstrated cause, repeat the fresh 10-headless/5-headed first-attempt baseline and actual UI/API/Mongo integration. Historical cached-browser results do not satisfy that gate.

## Bounded startup diagnostic bundle (2026-10-31)

Implemented additive diagnostics through the existing project-authorized Lab status/history API and Lab page. This is an observability change, **not a fresh-start fix**. Older records without a bundle remain readable. No legacy execution payload, feature default, dependency graph, retry policy, browser pin, network boundary or model integration changed.

The runner records the existing run ID/mode and stage timings, validated driver version, driver running/exit state and exit code, browser observation, DevToolsActivePort **existence only**, session-created boolean, fixed native error categories and separate cleanup observations. The active/failing phase now receives a duration even without a following transition. Browser observations use bounded native queries only over the runner's Job Object, with at most 64 process IDs per query and 32 retained Chrome query handles. Process handles are released after teardown. Cleanup polling has a one-second bound and does not retry session creation or the workflow.

Failure-time state is preserved separately from cleanup state. `driver_exited_job_closed` reports driver exit, closed Job Object and exit of observed Chrome processes; it does not prove every possible descendant was observed. `not_observed`/`unavailable` are explicit uncertainties. A process that was not sampled is not described as never launched. DevTools file contents/port/websocket URLs, image paths, PIDs, native lock names, environment values and raw browser/driver output are not included. Stderr is consumed in chunks of at most 8192 characters, reduced to fixed categories, and discarded. No category captured does not establish absence of native errors. API filtering independently rejects extra keys, invalid types, arbitrary strings, oversized exit codes and unapproved categories. UI adds an expandable **Startup diagnostic bundle**, including phase timings, to each new run.

### Current-task actual results

| Check | Environment | Result |
| --- | --- | --- |
| Initial fresh headless diagnostic probe | Actual Robot/direct WebDriver, controlled sample | Failed after 6.563 s; ChromeDriver and Chrome running before cleanup, DevTools file absent, no session. ReadTimeout. |
| Cached headless comparison | Actual runner, controlled sample, explicit existing CfT | Completed in 18.641 s; DevTools file present, session created, three screenshots. |
| Final fresh headless probe after cleanup/synchronization refinement | Actual runner, controlled sample | Failed after 9.391 s; browser-launch phase 5000 ms, both processes running, DevTools file absent, no session. |
| Cleanup for all three ordinary probes | Native job observations + separate harness CIM check | Observed Chrome exited, driver exit code 0, Job Object closed; no survivors observed. Exit code 0 alone does not mean the smoke completed. |
| Real cancellation with diagnostic handles | Cached CfT/sample, separate sequential run | Cancelled; one screenshot captured; no surviving child processes observed. |
| Runner suite/dependency check | Isolated runner, protocol fixtures/local proxy | 8 passed; pip check passed; exact installed graph test still excludes prohibited clients. |
| Lab authorization/service filtering suite | Mocked isolated API | 10 passed, including secret-canary filtering and malformed bundle types. |
| Existing feature/history suite | Mocked isolated API | 14 passed. |
| Lab UI suite | Intercepted API fixtures on task-owned Next server port 3109 | 3 passed, including failure bundle expansion, timing and retry availability; not real authentication/Mongo evidence. |
| UI TypeScript/focused ESLint | Static checks | Both passed. |

Fresh completions are **0/2**, retaining initial and final code revisions as separate attempts; cached completion is **1/1**. This is not the requested post-fix 10/5 reliability series. [Sanitized run evidence](evidence/startup-diagnostic-bundle.json) retains both failures, successful comparison and limits. The task-owned UI server was stopped. Existing user services were not restarted or killed. No new real UI/API/Mongo persistence verification, cloud test, fresh download or supported-current-release validation is claimed.

The configured fresh executable ProductVersion and driver --version were rechecked as **146.0.7680.31**. The user's ordinary Chrome version 156.0.8078.75 does not need to match: the server-owned WebDriver capabilities specify the exact CfT binary, never implicit discovery of normal Chrome. The successful cached session validates its full browser/driver match. A fresh failed session still cannot report its browser version through session capabilities.

Next: collect the scoped elevated native trace described above using run identity `e14f40ddef9a48ab800ea7c465f45793` as the failed reference (a new probe creates a new identity). The new bundle narrows the symptom to a running browser that has not published DevTools readiness; it does not identify why. Fix a demonstrated cause before rerunning full 10/5 and real integration. M1B remains deferred.

## Session timeout ownership experiment (2026-10-31)

The original five-second failure is **HTTPX ReadTimeout** from the client's default timeout during POST /session. It is not an explicit ChromeDriver session-not-created response. Driver readiness is a separate six-second polling budget; supervisor heartbeat expiry is six seconds with eight-second teardown grace; normal run total defaults to 90 seconds. No evidence of a browser crash before cleanup was found.

A separate sequential harness used 45-second session reads with a 65-second outer cleanup bound, unique writable profiles, same 146.0.7680.31 driver and matched fresh/cached browser payloads. Browser sandbox and Job Object remained enabled. Direct/minimal trials used about:blank; the custom-library trial used the controlled sample configuration. These are non-admin tool-launched processes, not a manually typed desktop-terminal reproduction. Separate Chrome logs and verbose driver logs remained in ignored private tmp storage. Transport was remote-debugging-port=0, not a pipe; the DevToolsActivePort existence check was appropriate. The direct/minimal arguments differ from the runner: this is a layer comparison, not evidence isolating individual flags.

| Layer | Fresh | Cached | Before cleanup |
| --- | --- | --- | --- |
| Direct Chrome, 45 s observation | Debugging port appeared at 16.063 s | Appeared at 0.937 s | Both running |
| Minimal HTTPX/driver, 45 s session read | ReadTimeout after 45.016 s; DevTools HTTP had responded around 12.7 s | HTTP 200 session in 1.453 s | Both running |
| Custom DirectWebDriver library, diagnostic 45 s read | Session created in 24.438 s after POST | Session created in 3.281 s | Both running in native snapshot |
| Actual supervised Robot path after narrow correction | ReadTimeout after 45 s; total 49.718 s; reached session_handshake, DevTools file present | Not rerun at this layer in this task | Fresh Chrome and driver running; observed exit only after cleanup |

The custom-library diagnostic changed the client's read setting for that trial, including teardown; its teardown timing is not comparable to production five-second command cleanup. The actual correction now applies 45 seconds **only to POST /session**; connect/write/pool and all other commands retain five seconds. No retries added. Nine runner tests pass, including a regression checking the exact per-request timeout split. This corrects a demonstrated premature client timeout but **does not resolve fresh startup**: the actual supervised verification still failed. Do not mark readiness or run a success-only baseline. Existing historical failures remain valid.

Driver logs narrow the remaining minimal-case stall: browser-level Target.getTargets and Target.attachToTarget responded, but Page.enable and subsequent page-session commands lacked responses before timeout; cached control answered these. These CDP commands were issued internally by ChromeDriver, not by model-generated code. Chrome logs showed background registration errors in the reduced fresh case and a restart-registration command-length warning in the runner case; neither is proven causal. No profile/permission/policy error was established. Do not copy raw logs into API/UI or infer causation from unrelated warnings.

[Timestamped sanitized evidence](evidence/session-timeout-study.json). Reproducer: `visual-runner/tests/timeout_diagnostic.py --fresh <fresh chrome.exe> --cached <cached chrome.exe> --driver <matched chromedriver.exe>`, run with the isolated runner Python. It creates private logs/profiles under ignored `tmp/timeout-study-*`, emits sanitized event records and supports a per-case `cancel` file; its watchdog closes the job. The explicit executable arguments and unique profile locations are developer configuration, never API inputs. Preserve these private files for local comparison; do not upload raw native logs. Browser downloads previously came from the official win64 CfT archive; cached download provenance is not independently established. All 308 common payload hashes matched in the prior current-checkout comparison; no new download was performed.

Next specific hypothesis: fresh renderer/page-target initialization stalls or is delayed after browser-level DevTools is already responsive. Compare renderer process/initialization diagnostics under the same runner flags, environment and profile root; vary one factor only after a repeated matched control. Real API/UI, the full 10/5 baseline and cancellation during the extended session call remain unverified for this correction. M1B remains deferred.

## Small ACL and launch comparison (2026-11-01)

No full 10/5 series was run. No permission/security setting or application behavior changed. Read-only ACL inventory found two Chrome capability entries on all 317 fresh and 326 cached entries, including directories. chrome.exe, chrome.dll and chrome_elf.dll inherit ReadAndExecute/Synchronize for both capability SIDs in both installs; all three have only normal data streams. This checks ACE presence/inheritance, not effective restricted-token access or parent traversal. C and F are NTFS. Defender history query was unavailable; no antivirus exclusion or sandbox bypass was attempted.

One actual supervised fresh headless attempt failed in 49.063 s at session_handshake with HTTPX ReadTimeout, DevTools file present and browser/driver alive before cleanup. Its immediate external cleanup probe reported one possible survivor and stopped; a later task-specific query found zero matching browser/driver/runner processes. Preserve the first unverified result rather than relabeling it a pass.

A separate two-attempt library-only comparison with private driver and Chrome logs created a fresh session in 11.422 s after POST and a cached session in 1.781 s. Both reported matching 146.0.7680.31 versions and running Chrome before teardown; observed processes exited during cleanup. These are session checks, not complete Robot workflows or a candidate fix. Both use the same driver, flags, working directory and profile root, separate unique profiles, inherited environment, sandbox and Job Object. The standalone library inherits parent environment whereas normal supervised execution filters it; private driver log redirection also differs from the runtime stderr pipe. Those differences prevent attributing success to a particular cause. No environment values or raw native logs are published.

The diagnostic harness adds `--layers runner` to select only this small comparison and captures private verbose driver logs in addition to Chrome logs. [Sanitized evidence and protocol event timestamps](evidence/small-comparison-nov01.json) retain all three attempts and cleanup uncertainty. Syntax and git diff checks passed. No application fix, full baseline, real API/UI rerun, effective-token access test or native process trace is claimed.

Next specific controlled test: run the logged library comparison under the same filtered OS environment as the supervisor, changing only environment inheritance. If that succeeds, isolate private-file versus stderr-pipe driver logging as a separate factor. Capture renderer/page-target timing before proposing a fix. Full 10/5 remains blocked until a candidate correction succeeds in the small comparison; M1B remains deferred.

## Environment and logging factors (2026-11-01)

The diagnostic harness now accepts `--environment filtered|inherited` and `--driver-log file|pipe`. Filtered mode replaces its environment with the same OS-only allowlist used by the supervisor, without publishing removed variable names/values. Only diagnostic tooling changed; no runtime fix or security setting changed.

Four sequential library session checks used the same browser/driver pair, sample server, profile root (unique profiles), Chrome diagnostic flags, Job Object and 45-second session-read limit. With filtered environment/private driver file, fresh created a session in 3.156 s after POST and cached in 2.234 s. Changing only driver logging to the normal stderr pipe, fresh succeeded in 2.531 s and cached in 1.766 s. These four successes are session checks, not completed Robot workflows or proof the factors never matter. Observed browsers were running before cleanup and exited afterward.

One subsequent normal supervised fresh smoke, without the extra Chrome logging flags, created a session but failed during navigation. Whole lifetime 22.172 s; screenshots remained absent. Its diagnostic code was null because Robot failure details are currently not propagated into the safe summary. External cleanup observation found no survivors. Do not call this a completed smoke or infer a navigation root cause from the missing detail.

[All attempts](evidence/environment-log-comparison.json). No full 10/5 series or real API/UI run occurred. Harness Python syntax and git diff checks passed. Prior failed attempts remain valid; no cold-install readiness, candidate fix or M1B advance is claimed.

Next bounded task: capture a fixed allowlisted error code from failed Robot keywords, then compare one fresh/cached navigation attempt with independent session and page-load timings. Keep normal command deadlines, sample origin restrictions, no retries and cleanup. Environment filtering and stderr/file logging did not reproduce the startup failure in this comparison; do not change those controls based on these results. Variable cold-start/renderer timing remains unresolved.

## Robot failure capture and navigation comparison (2026-11-01)

Fixed a diagnostic gap: Robot core absorbs keyword exceptions into its result, so a failed keyword previously left `diagnostic_code` empty. The four fixed keywords now retain only an allowlisted exception class/code before rethrowing. Unknown messages map to RUNNER_INTERNAL_ERROR; exception text/tracebacks are not copied into run state. Added fixed `navigation_checkpoint` and `screenshot` stages, accepted by the existing API sanitizer. No timeout, action, approval, dependency or origin changes.

A real Robot-core regression verifies a ReadTimeout containing a secret canary produces only the safe ReadTimeout code while still failing the suite. All ten runner tests and ten mocked Lab API tests passed. These are distinct from actual browser observations below.

| Actual supervised headless attempt | Result | Whole lifetime | Navigation evidence |
| --- | --- | --- | --- |
| Fresh initial | Failed, ReadTimeout, zero screenshots | 19.594 s | Coarse navigation phase 5797 ms; this process started before finer labels were added, so POST URL versus URL confirmation cannot be distinguished. |
| Cached control | Completed, three screenshots | 16.250 s | Navigation phase 547 ms; confirmation 407 ms. |
| Fresh final with finer labels | Completed, three screenshots | 42.563 s | Navigation phase 828 ms; confirmation 406 ms; most delay occurred before session readiness. |

Fresh workflow completion is **1/2**, cached **1/1**. All observed browsers were running before cleanup and exited after cleanup; external harness checks observed no survivors in all three. Stage timings describe intervals between stage callbacks, not isolated server-side processing or individual screenshot latency. [All attempts and screenshots metadata](evidence/keyword-navigation-comparison.json).

The diagnostics fix succeeds, and the existing separate session budget allows one fresh full workflow, but no correction to the variable browser/page initialization delay has been demonstrated. No full 10/5, headed series or real API/UI rerun occurred. M1A remains verification incomplete; M1B stays deferred. Next investigation should use the captured error/stage rather than treating every failed workflow as startup failure. Keep session-creation and navigation failures distinct; do not increase ordinary command timeouts or add retries based only on the intermittent success.

## File-state experiment and navigation deadline correction (2026-11-01)

Reviewed the new hypothesis as unproven: identical payloads/ACL entries do not establish identical filesystem/security state. A new task-owned copy of the cached directory was configured with the same sandbox-directory switch, without modifying the original. Six direct headless about:blank probes were interleaved fresh → cached → copied → copied → cached → fresh, each with its own profile, filtered OS environment, same arguments/cwd, 45-second endpoint observation bound and Job Object. No AV exclusion, administrator elevation, sandbox bypass or Dev Drive change occurred.

| Bundle | First endpoint observation | Second endpoint observation | Raw chrome.dll read + SHA256 |
| --- | --- | --- | --- |
| Fresh on F | 4.063 s | 22.391 s | 4.360 s |
| Original cached on C | 2.140 s | 0.515 s | 0.828 s |
| Newly copied cached on F | 15.703 s | 11.063 s | 3.093 s |

All six stayed alive until cleanup, published endpoint files, and observed Chrome exited during cleanup. DLL hashes matched. The copied cached bundle is slow too, so download/extraction is not the sole demonstrated distinction. But copy path/volume differs from original; raw hash timings include Python SHA256 work and warm files before launch. These observations support a path/storage/security-state hypothesis, not an antivirus diagnosis or proof of a specific per-file reputation mechanism. No twenty-launch series was run.

A concrete protocol-budget mismatch was corrected: ChromeDriver pageLoad is 10000 ms, while the client previously abandoned navigation after five seconds. POST to the active session's URL now has a 12-second read budget (ten-second page load plus two-second response allowance). Only session creation retains its separately named 45-second budget; GET URL, screenshots, inputs and ordinary commands remain five seconds. No retries, warm-up navigation or extra browser preflight were added. Named constants make these boundaries explicit. The total-run watchdog remains independent; the sums are not a guarantee every possible action tail fits the run budget. Its expiry must stop the run, not silently extend it.

This is a supported deadline-consistency correction, **not a demonstrated fix for browser initialization latency**. A focused protocol test asserts the exact session/navigation/ordinary timeout split and request counts; all ten runner tests passed. One actual fresh supervised smoke completed with three screenshots in 21.282 s; one cached control completed with three screenshots in 17.328 s. Their navigation phases were 0.640 s and 2.344 s, both below the old five-second bound, so these successes do not establish tail-latency improvement. Real cancellation reached Cancelled, with no surviving children observed. No survivors were observed after both smoke attempts.

The earlier eight-second screenshot stage includes the fixed eight-second inspection hold; it is not total screenshot capture time and must not be divided by three to estimate screenshot latency. Likewise, a navigation ReadTimeout does not prove cold page load is the cause. Extra about:blank warm-up could mask startup state and is not part of normal execution.

[All six direct attempts, timings and two candidate smoke checks](evidence/file-state-navigation-budget.json). Reproducer: isolated Python → `visual-runner/tests/file_state_diagnostic.py --fresh <fresh directory> --cached <cached directory>`. It copies only into a new ignored task directory and leaves installations untouched; raw logs remain private. The copy is diagnostic evidence, never installed as a runtime workaround.

Next: compare a newly copied cached bundle on the same C volume as the original to separate volume from new-path state, or use authorized read-only native/security telemetry to attribute delays. No security exceptions should be introduced. M1A remains implemented with incomplete reliability verification; no new full 10/5, fresh install, supported-release validation or real-login/API/Mongo run is claimed. M1B stays deferred.

## Same-volume cached-copy comparison (2026-11-01)

Extended the diagnostic-only `file_state_diagnostic.py` with `--copy-root` and `--pair-only`. A new task-owned cached-bundle copy was created in the Windows temporary directory on C, directory sandbox configuration succeeded, and the original cached installation stayed untouched. Both browser installations were on C; all four profiles were fresh distinct directories under the same F task root, with identical arguments, OS-only environment, cwd, Job Object and 45-second observation bound. This removes browser volume as a difference between the two installations, not every directory/permission or time-varying host difference.

| Order | Browser | Time to DevTools port file | Exit before cleanup |
| --- | --- | --- | --- |
| 1 | Original cached | 2.468 s | No; running |
| 2 | New copy on C, first launch | 12.594 s | No; running |
| 3 | Same new copy, second launch, unique profile | 0.797 s | No; running |
| 4 | Original cached | 2.671 s | No; running |

Observed Chrome processes exited during bounded cleanup in all four. chrome.dll read/hash values are retained in [sanitized evidence](evidence/same-volume-copy-comparison.json). These direct launches test endpoint-file publication, not WebDriver handshake or a complete workflow. The hash read before launch warms file contents, and new directory inheritance and background machine load remain possible differences. The new path is slower on the first attempt despite being on C, so an F-only volume explanation is insufficient. Faster second launch supports a cold file/path-state hypothesis but does not identify antivirus, reputation scanning or any specific Windows component. Earlier repeated fresh failures are not explained away by this one pair.

No application change, security exclusion, administrator launch, sandbox bypass, warm-up stage or runtime substitution was added. Harness syntax and git diff checks passed. No full 10/5 or UI/API/Mongo run occurred; M1B remains deferred. The diagnostic copy stays task-owned temporary evidence and is not used as a production fix.

Next evidence needed before another runtime fix: authorized read-only native file/image-load/security telemetry during a newly copied first launch versus its second launch, correlated to task-owned processes and timings. Do not solve cold latency by silently prewarming/retrying customer runs. The existing explicit session/navigation budgets remain bounded; their latest small successful smoke checks do not establish cold-install reliability.

## Matched stable 156 experiment, completed on resume (2026-11-02)

The official CfT last-known-good feed was checked before download on November 1 and rechecked on November 2 (feed timestamp 2026-11-01T21:09:51.406Z); Stable remains 156.0.8078.80. Used existing setup.ps1 with `-Version 156.0.8078.80 -InstallRoot F:\ai-qa-team\tmp\m1a-cft156-experiment` and the existing Python 3.12 interpreter. Both official win64 browser/driver archives downloaded and extracted, directory sandbox configuration completed, and full version verification matched. New runner dependencies remained isolated; normal Chrome, API site-packages, old 146 installation and the default setup pin were preserved.

| Actual supervised run | Full matched browser/driver pair | Completion | Total lifetime | Failure/cleanup |
| --- | --- | --- | --- | --- |
| New stable headless | 156.0.8078.80 / 156.0.8078.80 | 0/1 | 48.891 s | HTTPX ReadTimeout during session_handshake; Chrome and driver running, DevTools file present before cleanup; observed processes exited afterward. |
| Old fresh headless control | 146.0.7680.31 / 146.0.7680.31 | 1/1 | 25.734 s | Completed controlled workflow; observed processes exited during cleanup. |
| New stable separately headed | 156.0.8078.80 / 156.0.8078.80 | 0/1 | 50.062 s | Same handshake ReadTimeout; no pre-cleanup exit observed. |

The headed result was recovered from durable harness JSON after the usage-limit interruption; it was not rerun or omitted. Both failed first attempts stay in the denominator. All three harness cleanup checks observed no survivors. On resume, a separate process query found zero matching task processes. [Sanitized evidence](evidence/cft156-upgrade-experiment.json) records all stages and timings. Changing versions changes payloads and is an upgrade compatibility experiment, not proof a version itself causes the difference. The result shows the symptom is not eliminated by the current stable matched pair.

On resumed checkout the 156 isolated environment passed all ten runner tests (including exact allowed distribution graph) and pip check. No new real UI/API/Mongo, full 10/5, cloud or customer-app verification occurred. Installation succeeded; browser-smoke verification failed for the new pair. Do not automatically promote the new pair or claim supported-release readiness from installation/version checks alone.

Native telemetry remains unperformed: Process Monitor was unavailable, the execution token was not an elevated administrator, and WPR was idle. No machine-wide capture, driver installation, protection exclusion or administrator launch was attempted. Collecting a scoped kernel file/image-load trace requires a separately available authorized tracing session; mere WPR availability is not sufficient. No automatic fallback or runtime retry was added.

To reproduce the isolated upgrade installation from repository root:

```powershell
.\visual-runner\setup.ps1 -Python 'F:\ai-qa-team\.feature-flags.venv\Scripts\python.exe' -Version '156.0.8078.80' -InstallRoot 'F:\ai-qa-team\tmp\m1a-cft156-experiment'
```

Use that directory's matching chrome.exe/chromedriver.exe together for an explicitly labeled diagnostic run; never pair driver 146 with Chrome 156. The default old pin remains a historical controlled-development baseline, not a recommendation for production distribution. Next prerequisite for attributing the cold/path effect remains scoped native/security telemetry, with no security bypass. M1A is implemented but verification incomplete; M1B remains deferred.

## Native capture preparation (2026-11-02)

Downloaded official Process Monitor 4.12 to the ignored task tools directory and verified a valid Microsoft Authenticode signature. No trace, elevation, security change or browser rerun occurred. The current token is non-admin; the remaining interactive UAC step and pre-capture filtering are documented in [NATIVE_TRACE_GUIDE](NATIVE_TRACE_GUIDE.md). Tool download removes the missing-binary blocker, but does not establish native trace access or resolve browser latency. User-approved tracer elevation is separate from browser execution, which stays non-admin.

## First supplied native CSV review (2026-11-02)

User completed tracer UAC and manually configured filters because the automation helper cannot reliably control the higher-integrity window. The agent launched one probe, run 1adb2d68220b494b8383d8dab02163c5, supervisor PID 13784; it exceeded the harness process bound and the external CIM cleanup query timed out. Recovered state remained starting/driver_launch with no screenshots; this is incomplete IPC evidence, not proof of a live process. A later bounded query found no children of that supervisor. No second browser was launched in that capture turn.

The subsequently supplied local CSV contains 1046 events, all chromedriver.exe, from PIDs 16412 and 28056 with parent PID 12612. No Chrome/renderer events are present and no stored run metadata matches the captured driver PID. Therefore the trace is not safely correlated to the intended failing probe. The first process is a successful --version call; the second exits code 0 after approximately 21.7 seconds, with a 21.1-second event gap. A gap between filtered events is not an operation duration or proof of a hang. One registry All Access open was denied; it does not establish a permission root cause. No change is justified from this trace. [Sanitized review](evidence/native-csv-review.json). Raw CSV/PML remain private in ignored tmp.

Before another capture, simplify custom Include rules to one Image Path begins-with rule for the controlled 146 version's common binaries directory (containing both chrome-win64 and chromedriver-win64), keep Drop Filtered Events on, and correlate a newly launched probe's supervisor/driver IDs locally. Normal user Chrome must remain excluded. Capture must contain the task Chrome/renderer activity before attributing renderer initialization latency. No full baseline, M1B, retry or security bypass is authorized by these findings.

## Correlated Process Monitor capture review (2026-11-02)

The user saved the second capture over tmp/m1a-native-fresh.CSV/PML rather than the requested new filenames. The new CSV contains 68317 events: 1976 driver and 66341 Chrome events. Driver PID 17108 and browser PID 2844 parented by that driver establish correlation with run ef2c00d11b4e4b1893b44ee54efbd760. The actual run created a session, navigated and confirmed the sample URL, then failed on the first screenshot with ReadTimeout; external cleanup found no survivors. This capture is not a failed session-handshake trace.

No Load Image event failed. Main chrome.dll loaded 3.746 seconds after browser creation; the first renderer started at 8.728 seconds and loaded chrome.dll at 9.625 seconds. Registry and profile ACCESS DENIED events exist, but denial count is not root-cause evidence. Five temporary-file denials also have successful accesses by the same process to the same target; three utility-process attempts to list the parent workspace directory were denied. Their causal relevance is unknown without the working cached control. Do not loosen profile permissions from this evidence. Two renderer processes exited code 0 before final cleanup; that does not establish renderer crashes, while main browser/GPU termination aligns with cleanup.

[Sanitized review](evidence/native-correlated-review.json) stores source hash and correlation metadata. Raw trace/paths/command lines remain local in ignored tmp. CSV has no Duration column or call stacks; event gaps cannot be interpreted as I/O durations or antivirus scanning. This limits attribution. No runtime fix, security change, new browser run, full baseline or M1B was performed during analysis. Next: a single native cached control using the same driver, with its exact Chrome executable added to the image-path filter, and export operation Duration for both traces if available. Compare renderer initialization, screenshot interval and the same denied targets before claiming causation.

## Supplied cached native control review (2026-11-02)

Cached run 09c6fe8184904a118eed97f1d904e62f completed with three screenshots in 33.078 seconds; driver PID 17984 and external cleanup found no survivors. The supplied tmp/m1a-native-cached.csv correlates to that driver and includes its successful Process Create for the expected cached Chrome executable. However, all 2255 exported events belong to chromedriver.exe; there are no cached Chrome/renderer events. Therefore it cannot serve as a complete browser-side control for the fresh trace's 66341 Chrome events, and permission denial counts cannot be compared as if coverage were equal.

[Sanitized cached review](evidence/native-cached-review.json). No runtime fix, security change, additional browser launch or full series occurred during analysis. Next inspect the cached PML with current filters removed/replaced while capture remains stopped, searching for chrome.exe/child events for this attempt. If present, re-export those task-only events; if absent because dropped during capture, correct the filter before one further control. Do not collect unrelated processes or infer root cause from an incomplete control.

## Complete cached-browser native control (2026-11-02)

User saved the corrected control as tmp/m1a-native-second.CSV/PML. The CSV contains 86556 events (2405 driver, 84151 Chrome). Driver PID 14844 created main Chrome PID 29624, establishing correlation with run f29ea133f45e405ca67910fad1a182e6. This actual controlled smoke completed with three screenshots in 58.140 seconds, with no surviving processes observed after cleanup. Do not substitute this capture for the earlier driver-only control or merge their timing denominators.

Compared with the fresh screenshot-failure capture: cached main chrome.dll loads at +1.020 seconds versus fresh +3.746; first cached renderer starts at +5.494 seconds versus fresh +8.728. Both captures have successful image loads throughout. Cached registry RegOpenKey denials number 237 versus fresh 236, and RegCreateKey denials number seven in both. Cached profile denials number 17 versus fresh eight, including parent-workspace listing probes and temporary-file accesses. Thus these denial patterns occur in a successful run too; counts alone are not a basis for changing permissions. Cached also has browser-install-tree denials, classified in the evidence; no causal browser load failure follows from them.

[Sanitized full control comparison](evidence/native-browser-control-comparison.json) retains source hashes, identities, relative renderer timings and limits. Both CSV exports omit Duration and call stacks. Inter-event gaps do not measure individual I/O or CPU waits; no antivirus, disk, scheduling or renderer-crash attribution is established. No additional browser, security change, full 10/5 series, application modification or M1B work occurred during this review.

Next evidence can be obtained without another browser run: inspect the retained fresh/cached PMLs' long-duration event properties and associated stacks, or export the same task-only events with the Duration column. Focus on the fresh first-screenshot interval and main DLL initialization; compare the corresponding successful control rather than treating every denied probe as a defect. If stacks/operation durations show no responsible call, the next hypothesis is a scheduling/compositor delay not visible in these filtered file/registry exports. No new runtime timeout change is justified by these traces alone.

## Duration-export identity validation (2026-11-02)

Validated exported PID identities rather than trusting filenames. The file named m1a-native-fresh-duration.CSV has 86556 events from cached successful run PID 14844/main Chrome 29624. m1a-native-cached-duration.CSV contains the earlier 2255-event driver-only control PID 17984. The additional duration export is classified in [validation evidence](evidence/native-duration-export-validation.json). No duration export currently contains failed fresh driver 17108/main Chrome 2844. Therefore a fresh-versus-cached duration comparison cannot yet be made.

The complete successful cached trace has multi-second profile WriteFile/FlushBuffersFile events. Its longest NotifyChangeDirectory durations remain pending until cleanup and are not proof of synchronous blocking. Duration sums across concurrent/possibly nested events are not wall-clock execution time. These findings do not establish a scanning, disk or screenshot root cause. No runtime changes, new capture or browser probes were performed. Reopen the original fresh PML, verify PIDs 17108/2844 are present, then export Duration-bearing task events to a new filename before analysis. Do not rerun browsers merely to correct export identity.

## Correct fresh duration export and I/O findings (2026-11-02)

The user exported tmp/m1a-fresh-17108-duration.csv with the correct 68317 events and PIDs 17108/2844. Matched it against the 86556-event cached control duration export (misnamed fresh-duration, but correctly identified by PIDs 14844/29624). These are the original captured runs; no browser rerun occurred for analysis.

Fresh successful ReadFile operations on chrome.dll reached 2.272 seconds. Successful WriteFile operations on isolated-profile Network Action Predictor-journal and DataSharingDB-journal reached 3.852 and 3.334 seconds, with flushes around 1.1 seconds. Successful cached profile writes also reached 3.270 seconds and flushes 2.257 seconds. These are measured operation durations, unlike prior inter-event gaps; they support storage/profile I/O latency as an investigation target. They do not identify antivirus/reputation, storage hardware, scheduler or filter driver as the responsible component, nor prove background profile I/O blocked a screenshot.

Long pending NotifyChangeDirectory requests were excluded from slow-I/O interpretation. Concurrent/nested durations and counts cannot be summed as independent delays. Both runs used F-based isolated profiles; binary locations differ, and Process Monitor overhead is another confounder. No stack attribution is available from these CSVs. [Validated duration comparison](evidence/native-duration-comparison.json) preserves source hashes and sanitized file-operation groups; raw logs remain private.

Next controlled candidate experiment: keep one browser/driver pair, flags, environment and sample fixed while varying only unique profile location (current F runtime root versus a new private C temporary directory). Test as a diagnostic override first; do not silently relocate production data, disable protection, warm profiles, retry actions or declare the I/O hypothesis proven. The traced cached success having similar slow writes means a profile-location change may not resolve the failure. No runtime or security change, new probe, full 10/5 or M1B occurred in this review.

## Isolated profile-location comparison (2026-11-02)

Added developer-only `tests/profile_location_diagnostic.py`, which wraps the existing supervisor startup harness and changes only the unique Chrome profile path, with port-file diagnostics adjusted to the chosen profile. IPC, screenshots and sample server stay under the same F workspace; Chrome/driver binaries, flags, filtered environment, action sequence and deadlines are identical. The override lives only in the diagnostic child bootstrap; API inputs and normal runtime configuration are unchanged. C profiles are created under a new private task-owned Windows temporary parent, never normal Chrome profiles, and removed only after verified process cleanup with containment checked.

Four sequential fresh-bundle headless full Robot workflows, in order F/C/C/F:

| Order | Profile volume | Whole run | Navigation phase | Outcome |
| --- | --- | --- | --- | --- |
| 1 | F | 25.110 s | 860 ms | Completed, three screenshots |
| 2 | C | 15.719 s | 78 ms | Completed, three screenshots |
| 3 | C | 14.516 s | 62 ms | Completed, three screenshots |
| 4 | F | 15.407 s | 484 ms | Completed, three screenshots |

Both profile locations completed 2/2. All four external cleanup checks observed no survivors. [Every attempt and verified profile drives](evidence/profile-location-comparison.json). The last F run is comparable to C, so profile relocation is not an established correction. The slow first F attempt may reflect order, cache warmth or host activity; these results neither prove nor rule out a storage/security effect. No failure was reproduced in this small comparison. No production profile relocation, warm-up stage, retry, security bypass, full 10/5 or real UI/API/Mongo verification was performed; M1B remains deferred.

Harness syntax and help invocation checks passed; git diff --check passed with line-ending warnings. Normal application code did not change in this task. The next evidence should target the retained slow chrome.dll ReadFile operation's stack and corresponding cached operation, rather than infer cause from volume alone or expand timeout budgets. A quiet successful sequence is insufficient to establish a fix for the earlier intermittent failures.

## Isolated Linux image preparation (2026-11-02)

User authorized an isolated Linux runner image as a bounded alternative OS probe.
Implemented image definition and standalone container launcher in
`visual-runner/linux/`; detailed commands and limits are in its README. This is
mechanical M1A feasibility work, not M1B. It reuses fixed Robot keywords, the private
synthetic app/proxy and direct HTTPX client. Only process-tree construction and the
supervisor entrypoint gain injectable defaults; normal Windows API behavior stays
unchanged. Linux entrypoint is non-root/headless, takes no customer URL/config,
maintains heartbeat and cancellation, and has a bounded outer deadline. Process
Group SIGKILL is best effort inside the final container boundary; Linux per-browser
cleanup observation is explicitly unavailable. No cleanup success is claimed.

Current checkout: dev at 2479de4017cd8e29516daa1ecf62d5763bc2b6b2 with preserved
pre-existing user changes. Actual verification: three new mocked Linux spike tests
passed; ten existing runner tests passed outside tool sandbox. Initial restricted
run had three temp-file/socket permission errors, not browser failures. Linux Python
syntax and git diff --check passed (existing CRLF warnings only). Image dependency
validation is installed as a build gate, not yet an installed-image graph result.

NOT RUN: image build, Linux browser/sandbox/coordinates/three PNGs, cancellation,
timeout and forced-container cleanup, Linux UI/API/Mongo or GCP. Docker/Podman CLI
absent; WSL outside sandbox reports no installed distributions. No gcloud CLI found.
CfT 146.0.7680.31 remains an explicit historical OS-comparison pin; no claim of a
current security release. Python base/apt packages are not digest/snapshot locked.
Do not promote/deploy until actual build, sandbox and license/SBOM gates pass.
Windows startup remains unresolved and the earlier 10/5 failures remain recorded.
No fresh Windows baseline was rerun. Next: provision a local Linux container engine,
then execute the documented single-smoke/cancel/timeout gates. A cloud job requires
its own development project and deployment scope; no production readiness implied.


## Local Linux real-container verification (2026-11-02)

Podman 6.1.4 is now available. User built image
0ed93d0c910bb9a8769f34b3bd8b74e303aa24171292b15875162589ddec00dd;
user manual smoke completed with three PNGs/exit 0/no OOM; separate manual
cancellation recorded cancelled/exit 1/no OOM. These are user-supplied results.

Agent real-container baseline: 3/3 first-attempt completions, three PNGs each,
21.156/20.656/18.062 seconds including control and artifact-copy overhead.
Forced-stop 1/1: active session then SIGKILL, exit 137. Diagnostic-only two-second
supervisor timeout 1/1: timed_out, exit 1, 9.438 seconds including overhead.
Final inspections: all five exited, PID zero, no OOM; no running containers.
Per-browser cleanup telemetry remains unavailable. Filled/confirmation PNGs from
first baseline visually inspected: synthetic inputs and $60 confirmation visible.
This remains a mechanical check, not an automated business assertion engine.

Forced kill leaves the last state running: external reconciliation is absent.
Whole-output copying initially failed on Windows Linux-profile symlinks; allowlisted
state/PNG copies recovered the SAME killed attempt. No workflow replay or discarded
browser attempt. Stopped task containers/volumes retained for diagnosis.

See [sanitized evidence](evidence/linux-container-checks-nov02.json) and
[exact commands/limits](../../visual-runner/linux/README.md).
Three mocked Linux spike tests rerun: PASS. Harness syntax and git diff --check:
PASS (existing CRLF warnings). No normal runtime/image/API/UI changes this task.
Remaining: outer-watchdog/hung-browser fault tests, stale-state reconciliation,
Linux API/UI/Mongo integration, cloud sandbox/leases/artifacts and license/SBOM.
Windows blocker unresolved. No M1B, cloud deployment or customer readiness claim.


## Linux interrupted-state and outer-watchdog verification (2026-11-02)

Implemented an opt-in local Podman controller and fixed image helper. The controller
requires a managed container name/label, stopped/exited state, PID zero and dedicated
output volume. It uses that container's original immutable image ID, not a mutable
tag. Active/unmanaged containers are refused. Nonterminal state becomes interrupted
with exit provenance/no replay; existing evidence is retained, terminal records
are untouched and a second reconciliation is a no-op. The entrypoint now preserves
state/evidence on unexpected child exit and records timed_out for its outer deadline.
This is not an automatic daemon, Mongo reconciliation or distributed fencing.

Built separate :guard image ec46ed0f56ad43fcbc07122fbe5450e42bd755f9a7862027ba57556a2d6723fc;
original :local image unchanged. Build dependency guard passed; cached browser/pip
layers reused, so this was not a fresh download/install repetition.

Real local container results (first attempts, one each):
- Forced termination/reconciliation: exit 137, PID zero, no OOM; running -> interrupted;
  evidence references retained; repeated reconciliation unchanged; no replay.
- Frozen child supervisor: actual unchanged 100-second parent deadline + ten-second
  grace; container exited after 111.375 seconds, exit 1/PID zero/no OOM; terminal
  timed_out with one screenshot reference retained. Reconciliation left it unchanged.
- Normal completion: 14.391 seconds to container exit; exit 0/PID zero/no OOM;
  completed with three screenshot references, terminal metadata byte-identical
  after both reconciliation calls. This is separate from the earlier 3/3 baseline.
- All three active reconciliation requests rejected before helper launch.

Eight focused unit tests passed (process mocks, active/unmanaged refusal and real
local temporary-file idempotency/evidence/terminal preservation). Syntax and
 git diff --check passed with existing line-ending warnings. Evidence:
[guard report](evidence/linux-guard-checks-nov02.json). Commands and scope:
[Linux README](../../visual-runner/linux/README.md#guard-image-local-reconciliation-and-unchanged-outer-watchdog).

Files: linux/reconcile.py (fixed state helper); linux/entrypoint.py (preserve state
and distinguish outer timeout); tests/linux_reconcile_control.py (stopped-container
identity gate); tests/linux_guard_checks.py (real fault injection); expanded
 tests/test_linux_spike.py. No API/UI/job-consumer/dependency/browser changes.
No cloud resources, production data, M1B, retry or security bypass.

Remaining: Linux API/UI/Mongo integration with durable identity/leases, cross-host
fencing and automatic reconciliation; cloud sandbox/network/resources/artifacts;
retention and release/license review. The local controller requires one operator
and no manual container restart during reconciliation. Profiles remain private in
retained volumes after forced kill; cleanup telemetry is container-boundary evidence,
not per-browser confirmation. Windows startup latency remains unresolved. Next
bounded task is Linux adapter dispatch design before changing the existing app;
GCP feasibility remains a separate explicitly scoped deployment task.


## Product scope amendment: bounded parallel execution (2026-11-02)

The user accepted two isolated simultaneous jobs plus queueing as an MVP/demo
requirement. See MVP_SPEC and DECISIONS A11 for authoritative scope and
IMPLEMENTATION_PLAN for migration/gates. This amendment is documentation-only.
All Linux evidence above remains sequential; singleton API/process guards are
still implemented. No parallel execution claim, new browser test, lock removal,
M1B authorization or cloud deployment follows from the amendment.


## Batch execution scope refinement (2026-11-02)

Accepted target: one container per batch of 1-10 approved cases, sequential cases
and fresh sessions for independent cases, two batch containers concurrently, at
most two active cases/browser sessions. Additional batches queue. Per-case version,
status/evidence/outcome and budgets remain distinct from batch summaries/budgets.
See MVP_SPEC and decisions A11/A12 for authoritative semantics. Current synthetic
smoke remains single-case; no batch/parallel behavior or runtime verification was
added by this documentation-only amendment. No M1B or deployment authorization.


## Synthetic Linux batch backend delivered (2026-11-02)

The explicitly authorized contracts/backend task now implements a default-off,
development-only batch API and local dispatcher. See [execution contracts and exact
commands](EXECUTION_CONTRACTS.md). Canonical Pydantic models generate a committed
runner schema with a drift check; isolated validation adds no dependencies. It
accepts only 1-10 repetitions of the fixed synthetic form, not customer test specs,
URLs, credentials, code or AI calls. Per-case verdict is null; completion remains
Browser smoke check completed. Subscription counters are unchanged (unbilled dev).

New visual_runner_batches flag requires visual_runner_lab and dev/local/test. Routes
provide authorized start/list/status/cancel and private per-case PNG access. Separate
Mongo visual_batches/visual_batch_dispatch records pin immutable image/manifest and
own two slots. Conditional idempotency/slot/queued-state updates, fair bounded queue
selection, lower account/project caps, deterministic container identities and a
single-host/checkout kernel-locked controller preserve old execution data/consumers.
No automatic start/replay during recovery. Unknown post-start container disappearance
holds capacity rather than guessing safe termination. Per-case isolated sessions,
evidence and limits are run sequentially within each container; additional batches
queue. Old Windows start is rejected only while the new batch flag owns capacity;
old status/cancel/history/artifacts remain. Default-off old behavior is preserved.

Verification (explicitly separate environments):
- 10 batch contract/API tests passed with auth/DB/engine doubles where stated.
- 10 legacy Lab + 14 feature/history regression tests passed; initial flag expectation
  failures were updated for the intended new false default.
- 10 runner protocol/graph/lock/proxy and 9 Linux guard/batch-cleanup tests passed.
- Real task-owned TLS Mongo + Podman + ASGI backend: full post-fix fixture 10/10
  checks; subsequent focused final-backend fixture 10/10 checks. Authentication was
  a fixture double; project membership, Mongo, containers, browser, evidence were real.
  The full fixture qualified one 10-case sequential batch (10/10 completed cases),
  while the focused run intentionally did not repeat it after backend-only evidence/
  disabled-restart changes. Both recorded overlapping case intervals at peak two,
  with fresh sequential sessions, third-batch queueing, independent cancellation,
  private artifacts/cross-project denial, coordinator reconstruction/no replay and
  released capacity. Final fixture additionally raced eight real Mongo slot claims
  (one winner) and exercised a new disabled-feature controller's stop/reconciliation.
- Image b5d5e83e29ec11e6d2e34ce387f1e2f6f7108acdbd31bf22d96e4418a4dbb66c
  built and dependency/schema gates passed; existing pinned install layers reused.
- Schema drift and git diff --check passed (existing CRLF warnings).

Retained failures: first fixture could not start Windows TLS Mongo because it reused
one certificate as CA/server; fixed the fixture to use a signed leaf. First actual
integration exposed cancellation relabelled interrupted by remnant observation;
fixed it so cancellation ends the container without falsely changing the outcome,
while remnants still block the next case. That failed attempt remains in the
[summary](evidence/linux-batch-dispatch-summary.json), separate from
[full post-fix](evidence/linux-batch-real-full.json) and
[focused final-backend](evidence/linux-batch-real-final.json) evidence. No automatic
workflow retries were added. The restricted sandbox ASGI run stalled; focused
checks were run outside it against doubles/isolated services as labelled.

NOT VERIFIED: real login/UI batch flow, full API-process restart/hard-kill with
batches, DB outage/engine disconnect, multi-host coordination, large-queue fairness,
account dollar budgets/entitlement settlement, hostile customer networks, cloud
sandbox/resources/storage, current-release/security/SBOM promotion. No batch UI was
added. This is not a complete business executor, production readiness or a Windows
fix. Missing evidence is marked incomplete; private local artifacts/volumes require
retention management. Next bounded task: batch UI + actual development-login flow
and process-level fault qualification, before customer scope. M1B remains deferred.


## Batch UI delivered (2026-11-02)

The existing project Visual Runner Lab now mounts Linux batch controls only with
both development flags enabled and a signed-in member identity. It starts 1-10
synthetic fixture repetitions, displays queued/active/terminal batches and ordered
case outcomes, supports independent cancellation and lazy private evidence, and
preserves old single-smoke history. Customer URLs/test selection remain unavailable.
A count/idempotency key is retained per member/project through ambiguous start
responses and reloads; only explicit resolution resends that same initiation key.
No automatic browser replay is introduced. Polls stop when idle and pause while
hidden; manual refresh/visibility regain refresh history. The backend still owns
capacity/auth, and no entitlement charges were added.

Types come from canonical Pydantic models via the extended exporter; JSON Schema
and generated TypeScript drift checks are part of the ten passing contract/API
unit checks rerun this task. UI checks: nine unique intercepted browser regressions
passed (first prepared run 8/9, focused failed-test correction 1/1). The assertion
was corrected from three image transports to three unique protected artifact IDs
because Strict Mode starts/aborts effects twice. The initial navigation timed out
before the fixture Ready log (183.2s); a later route preflight returned HTTP 200.
No application startup timeout inflation or security bypass. Screenshot of the
seeded queue/running/cancelled view was visually inspected. These use fake API/auth,
not real-login or Mongo/Podman end-to-end verification. Prior backend real-service
results were not rerun. See [UI evidence](evidence/visual-batch-ui-nov02.json) and
[commands/limitations](EXECUTION_CONTRACTS.md#batch-ui-verification-and-operation-2026-11-02).

Changed: existing Lab page/feature-key type; new VisualBatchLab and shared
LabScreenshot; generated TS/exporter/drift assertion; new intercepted UI tests.
No backend runtime/runner/dependencies/config secrets changed. Final TypeScript, focused lint (zero warnings), generated contract drift and
git diff --check passed; only pre-existing CRLF notices remain in diff output. No M1B, customer-app execution, cloud,
commit or push. Next is real development-login/UI/API/TLS Mongo/Podman qualification
and batch process-fault coverage, not a readiness claim from intercepted tests.


## User-observed Linux batch startup failure (2026-11-02)

After the user's local UI attempt, retained real IPC for batch
ad254f1a480842a68e94094eb73408de/case 48e0951c87f8451db24417c2d0482e61
shows HTTPX ReadTimeout during POST session creation, last stage session_handshake.
Stage observations: browser_launch 37667ms, devtools_connect 5739ms, session_handshake
1851ms. Driver ready, DevTools file present, session_created false; no navigation or
screenshots. The configured session read limit is 45 seconds. This is a client
transport deadline, not an explicit ChromeDriver session-not-created response.
Actual container inspection: exited 1/PID zero/no OOM, image b5d5e83e29ec..., 2 CPU/
2 GiB limits. Driver cleanup exit -9 is not evidence of a pre-cleanup browser crash;
browser-level observation remains unavailable. Two later retained batches completed
three cases, with session setup stage totals around 1-3 seconds. This supports
intermittent Linux startup latency as an unresolved observation, not a proven cause.
The three batch records contain four cases: one failed and three completed. This is
user-driven local evidence; normal login/full API lifecycle was not independently
reverified. Prior passing fixtures do not erase this failure.

[Sanitized retained evidence](evidence/linux-batch-user-startup-timeout-nov02.json).
No new browser probes, timeout increases, retries, security changes or application
fix were performed. Next diagnosis: expose already-sanitized stage/timing data in
batch case evidence and compare bounded cold/warm Linux starts with resource
telemetry. Cold cache/VM/host resource effects remain hypotheses, not findings.


## Per-case startup evidence display (2026-11-02)

User reported the same synthetic check succeeded on rerun. That does not establish
a root-cause fix or erase the failed startup. This task adds observability only;
further cold/warm probes are deferred, with no change to existing M1B/customer gates.

CaseResult now carries optional sanitized startup_stage/reason/timings/diagnostics,
using the existing StartupDiagnostics model and safe_snapshot filtering. Future
collection persists these fields. Older records can be enriched at response time
from retained local sanitized IPC, without engine calls, Mongo backfill or changes
to their historical state/evidence. Missing cache remains explicitly unavailable.
Canonical models generate the updated UI types, including Record<string, number>
for timings. No runner wire/image change or rebuild is required.

UI: View evidence -> Startup diagnostics shows last stage, timings, session-created
observation, driver/browser observations and cleanup results. Unknown observations
remain unknown; cleanup-induced -9 is not presented as a browser crash. No raw logs,
commands, ports, environment or filesystem paths are newly exposed. Existing route/
project authorization still covers all response fields and artifacts.

Checks: 11 isolated contract/API tests passed, including canary removal and read-only
legacy enrichment with unchanged original data/files and no engine invocation.
Two focused React markup tests passed for failed-start details and unavailable
historical diagnostics; TypeScript passed. Final focused lint (zero warnings), export drift and git diff --check passed
(existing CRLF notices only). An intercepted browser-display fixture was added for future regression runs
but not executed here. Existing nine UI checks are historical, not rerun in this task.
No Linux browser probes, live end-to-end rerun, timeout inflation, retries, security
changes, deployment, commit or push. [Evidence](evidence/batch-startup-display-nov02.json).
Restart the development API and reload the UI to see newly available historical
startup details where retained IPC exists; no browser image rebuild is needed.

Case-specific missing session observations remain null/Unknown, and missing cleanup
remains unverified; the legacy single-smoke diagnostic schema was not changed.


## Per-check dispatch qualification (2026-11-02)

Implemented: one isolated container per synthetic check; a batch is an aggregate
parent. The shared global/account/project pool defaults to five configurable slots
(1–10), independent of the batch size limit ten. Canonical CheckDispatch validates
one-case identity/budget; new public records identify parallel-checks-v1. Old
sequential manifests/history remain unchanged and their containers drain before
new checks launch. The existing v1 :batch image is reused with one case per container.
No new dependencies, browser flags, timeouts, whole-run retries or M1B features.

Private additive visual_batch_checks records and a check-pool ledger own independent
launch intent, cancellation, evidence and reconciliation. Five initial preparations
are concurrent after durable reservations. Stop/collection cycles are independent;
parent cancellation is checked before start, feature-off still reconciles, and old
Windows starts reject occupied Linux ledgers even with the batch flag off. The
existing local kernel lock remains the controller boundary; no multi-host guarantee.

Actual real-service attempt: private TLS Mongo plus actual Podman/Robot/HTTPX/CfT,
with an explicit ASGI authentication double. Eight duplicate POSTs produced one
parent and five child identities. **0/5 checks completed**: all failed ReadTimeout
at browser_launch, after driver readiness but before a DevTools endpoint/session.
Browser-launch stage observations were 45.4–46.7 seconds; full case intervals were
about 50–63 seconds. No screenshots; five ready browser sessions were not observed.
Cleanup-induced termination is not evidence of a browser crash. Original evidence:
[evidence/parallel-checks-five-attempt1.json](evidence/parallel-checks-five-attempt1.json).

A separate one-check control was **incomplete**, failing during Podman container
inspection with ENGINE_UNAVAILABLE. The then-existing exception wrapper combined
OS process-launch failures and 30-second command timeouts; precise ownership cannot
be recovered from that report. The engine now attaches private fixed categories
command_timeout/process_launch_failed/command_failed, without raw commands/output
or changes to API diagnostic exposure. This instrumentation has a passing mock
regression but was not rerun against the failing engine.

Podman configuration reported four CPUs/2048 MiB; the Linux guest later reported
3803 MiB total/3292 MiB available/no swap in use. One direct container inspection
reported exited/1/PID0/OOMKilled=false. These observations do not establish or rule
out resource pressure during startup. No VM resizing, sandbox/security changes or
engine restart was performed. No causal startup fix was demonstrated.

A later ownership-checking cleanup probe verified one of the five exited/PID0;
four inspections were unavailable and the control identity was reported missing.
Do not claim all six were independently cleaned up: engine unavailability limits
that observation. The fixture attempted bounded cleanup and stopped only its own
Mongo process; no unrelated user service/container was intentionally stopped.

Final regression checks: 21 batch contract/auth/dispatch tests, 11 existing Lab
tests and 14 feature/history tests passed with doubles; TypeScript passed and
generated-contract drift passed. A newly added cancellation regression initially
failed and was corrected before the final passing batch suite. No intercepted UI
browser suite or normal-login path was rerun. Focused lint/final whitespace status
is recorded in [summary](evidence/parallel-check-dispatch-nov02.json).

The qualification harness now records bounded, read-only session-live intervals
inside each fixture container and intersects those observations. That replaces
the initial fixed-time snapshot, which could miss late startups. This revised
observer is syntax-checked only, not real-engine verified. It changes no runner
budgets or browser actions. Cancellation/restart/feature-off real tests remain NOT
RUN in this slice because the completion gate failed.

Verdict: **per-check dispatch implemented; five-browser verification incomplete**.
Next: establish reliable bounded Podman inspection/control, repeat a single
synthetic control with the new diagnostic categories, then qualify five simultaneous
established sessions and fifteen private PNGs with new identities. Do not rerun
old jobs or proceed to M1B/customer URLs. Commands: EXECUTION_CONTRACTS.md.

Changed implementation files for this slice:

- API app/config.py: configurable global/account/project check caps (default five).
- API app/models/visual_batch_model.py: explicit strategy/adapter and private CheckDispatch.
- API app/services/visual_batch_service.py: per-check materialization/dispatch, parent aggregation, independent reconciliation and legacy draining.
- API app/services/visual_batch_engine.py: private sanitized command failure categories.
- API app/services/visual_lab_service.py: occupied Linux capacity blocks Windows starts during feature-off reconciliation.
- API tests/test_visual_batches.py and tests/test_visual_lab.py: final 21/11 regressions.
- API tests/run_visual_check_parallel_real.py: private real-service qualification harness.
- UI src/types/visual-batch.generated.ts and components/visual-lab/VisualBatchLab.tsx: generated strategy identity, counts and concurrency explanation.
- MVP scope/contracts/plan/decisions, root guides and runner READMEs: revised scope and evidence/limits.

Final static verification: focused UI lint passed with zero warnings; TypeScript
passed; generated-contract drift and git diff --check passed (existing CRLF notices).
The revised interval observer and changed Python modules passed py_compile. No
additional five-browser attempt, cloud, commit, push or unrelated installation.


## Preparation diagnostics and reproduction (2026-11-03)

Verdict: the diagnostic-loss defect is fixed; the historical pre-start failure is
not reproduced or causally fixed. Old batch c733e3b859724c29a564cc0eadb0c979 remains
unchanged. Its saved manifest proves the workspace write occurred, but the old
records do not identify the next failing operation. A bounded historical Podman
container-event query returned no events; this does not prove no creation occurred.

Demonstrated code defects: launch saved ENGINE_UNAVAILABLE, reconciliation replaced
it with DISPATCH_INTERRUPTED, and parent aggregation dropped the child diagnostic.
The new code preserves the original diagnostic and adds typed, bounded preparation
metadata to cases. Stages: workspace, image_lookup, volume_create, container_create,
manifest_copy, parent_authorization, launch_intent and container_start. Each stage
has UTC start/completion/failure events and elapsed milliseconds. Only fixed stage/
reason enums escape; no raw stderr, commands, environment or filesystem paths.

The trusted engine thread waits for durable Mongo progress before each preparation
command. Metadata persistence has a 10-second bound (11-second thread wait); failure
aborts preparation. These are metadata bounds, not increased browser budgets.
Existing 30-second engine commands, 45-second session read, 90-second case budget,
network restrictions, sandbox, image and no-replay behavior are unchanged. API
request handlers still do not run the browser. No CDP adapter or M1B was introduced.

UI: View evidence -> Container preparation shows the typed timeline, timings and
first failed stage/reason. Browser startup remains a separate section. Old records
without preparation data do not invent a timeline. Restart the development API
and reload the UI to use the change; the pinned runner image needs no rebuild.
There is no backfill, replay or modification of existing histories.

### Actual checks, not historical reruns

All real fixtures use private task-owned TLS Mongo, the actual authorized project
routes/service/Podman/Robot/HTTPX/CfT path and synthetic sample data. Authentication
is an explicit ASGI double; project membership and artifact checks use real Mongo.
No normal user login/UI or full API-process restart was qualified here.

| Check | Environment | Actual result |
| --- | --- | --- |
| Initial one-case control | Real service/container; auth double | 1/1 completed, three PNGs; session-live observation 11.05s |
| Five-case first attempt | Same real path, independent containers | Preparation/start 5/5; workflow completion 4/5; 12 PNGs; one BROWSER_SESSION_NOT_CREATED at browser_launch |
| Five-session overlap gate | Read-only bounded in-container observations | NOT PASSED: only four established sessions observed; no five-way claim |
| Separate five-case cancellation after coordinator reconstruction | Same real path | 5/5 cancelled; all ten full-fixture containers terminal/PID0 and slots released |
| Missing-image fault injection | Real private Mongo + actual local image lookup | Expected image_lookup/command_failed retained through reconciliation and API; no browser launched |
| Final fresh one-case control | Same real path | 1/1 completed; all three PNGs authorized/private; cross-project artifact/cancel denied; container exited/PID0; slots empty |
| Preparation regressions | Explicit engine/DB doubles | 4 passed; each command failure, original error preservation, parent propagation and process-loss last-stage retention |
| Existing dispatch/auth contracts | Doubles | 21 passed |
| Existing Visual Lab | Doubles | 11 passed |
| Existing feature/history checks | Doubles | 14 passed |
| React preparation/startup markup | No services/browser | 4 passed |
| TypeScript | Static | Passed after correcting optional events handling |

The full five-case fixture intentionally exits nonzero because its completion and
five-session overlap gates failed; successful cancellation/authorization checks do
not turn that report into a pass. The two one-case controls are 2/2 independent
completions; do not hide the failed case in the five-case denominator. The missing-
image fault is deliberate and excluded from browser-startup completion counts.

The failed browser case reached container_start successfully. ChromeDriver returned
an explicit session-not-created response, categorized browser_exited; that is
separate from the historical HTTP ReadTimeout and from container preparation.
It does not establish a physical browser crash or a resource cause. No whole-run
retries, sleeps, sandbox changes or host/VM resizing were used to make a gate pass.
No surviving task container init processes were observed in the full-fixture terminal
checks (all PID0); no claim about unrelated host processes or production cleanup.

Evidence: [initial control](evidence/preparation-one-nov03.json),
[five-case attempt and cancellation](evidence/preparation-five-nov03.json),
[final fault/control](evidence/preparation-final-control-nov03.json).

### Reproduction and regression commands

From repository root, use an unused output directory (the fixture refuses reuse):

```powershell
.\.feature-flags.venv\Scripts\python.exe -X utf8 ai-qa-team-api/tests/run_visual_check_parallel_real.py --podman 'C:\Users\ram\AppData\Local\Programs\Podman\podman.exe' --image b5d5e83e29ec11e6d2e34ce387f1e2f6f7108acdbd31bf22d96e4418a4dbb66c --output tmp/preparation-control-new --quick
```

Quick mode now deliberately tests missing-image diagnostic retention before a fresh
one-browser control, three authorized screenshots and capacity release. It never
replays an old execution. Omit --quick for five-check/cancellation qualification;
do not rerun it automatically to erase a failed attempt.

From ai-qa-team-api:

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_preparation.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_batches.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_lab.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_feature_flags.py -v
```

From ai-qa-team-ui:

```powershell
node --test tests/preparation-evidence.test.cjs tests/startup-evidence.test.cjs
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
.\node_modules\.bin\eslint.cmd src/components/visual-lab/PreparationEvidence.tsx src/components/visual-lab/VisualBatchLab.tsx
```

No live/intercepted UI browser suite, normal-login qualification, runner dependency
census, clean Windows series or cloud check was rerun. The unchanged image was not
rebuilt. Existing dependencies/lockfiles, customer records and legacy consumers
were not modified. No commit/push/deployment.

Changed: visual_batch_model.py, visual_batch_engine.py, visual_batch_service.py,
generated UI contract, PreparationEvidence.tsx/VisualBatchLab.tsx, new focused
regressions and the private real-fixture harness. Source of truth remains the
Pydantic model; the runner manifest schema is unchanged. Next bounded task:
separately diagnose the explicit ChromeDriver session rejection under five-way
load, then repeat the failed gate only after a candidate fix. Normal-login UI
qualification and the historical Windows blocker remain separate. No M1B.

Final static checks for the Nov03 preparation task: focused lint, TypeScript,
generated-contract drift, Python compilation and git diff --check passed.
[Consolidated verification](evidence/preparation-verification-nov03.json) separates
real-service, fault-injected, doubled and NOT RUN checks.


## Current scope amendment: bounded Linux M1B (2026-11-03)

DECISIONS A14 now permits a bounded synthetic Linux M1B experiment alongside open
Windows and Linux five-way reliability work. This changes the development gate;
it does not change any historical result above. Five concurrent Linux check slots
remain the MVP target/default, with one isolated container per check. The user's
successful parallel two-check UI report has no supplied batch identity/independent
verification in this scope task. Latest measured five-way workflow result is 4/5.

See MVP_SPEC and IMPLEMENTATION_PLAN for the visible-button first milestone,
bounded wait/scroll, independent negative/positive assertions, temporary observation
images with selective durable evidence, and latency/usage limits. No M1B application
code, model calls, browser runs or concurrency setting changes are made by this
amendment. Customer/production/cloud access and readiness remain gated. Earlier
blanket M1B deferrals describe the decisions at their historical checkpoints and
are superseded only for this bounded Linux experiment.

### Project scenario and test-case navigation, 2026-11-10

Project navigation now includes Scenarios and Test Cases under their existing
feature gates. The new pages read 50 records at a time from membership-authorized
project-list endpoints, capped at 100 records per request. Scenario review reuses
the existing approval/test-generation dialog. Test-case details show stored steps
and expected results and link to the scenario catalog and execution approval.
Legacy generated status is displayed as stored and does not establish visual-run
approval. These pages do not initiate browser sessions.

AuthProvider now uses the existing User type, and story-loading callbacks declare
their dependencies. The related dashboard uses typed partial usage/limit fallbacks.
The focused backend suite passed 20 tests with doubles, including disabled gates,
foreign-project denial, project query scope and pagination bounds. Browser UI and
real MongoDB verification for these new catalog pages have not been run.

Final catalog checks passed TypeScript (`tsc --noEmit --incremental false`),
focused ESLint on 13 affected UI files with zero errors/warnings, and
`git diff --check`. Dashboard onboarding visibility is derived from user/project
state with explicit dismissal instead of synchronous state updates in effects.
These results apply to the local checkout; changes have not been committed or pushed.

### Catalog authoring and workspace navigation, 2026-11-10

Project catalogs now expose owner edit/delete actions. Scenario edits require
renewed approval. Test-case edits preserve structured action fields and immutable
visual snapshots; source digests require renewed visual approval. Deletion rejects
dependencies/approved versions/history and asks for UI confirmation. This is
single-request local CRUD, not distributed mutation/approval race qualification.
Manual basic test drafts use current subscription limits. Scenarios can be added
or AI-generated from a story in the catalog. Test cases can be manually authored
or generated from approved scenarios using the existing deterministic mapper.

AI Configuration is now a Workspace navigation entry with an administrator-project
selector. Credentials remain project-scoped and existing project URLs remain valid.
Workspace-wide shared credentials were not introduced. Repositories UI is hidden by
`FEATURES__REPOSITORY_UI=false` in the local backend .env. Its default-off flag also
guards direct navigation. Existing repository APIs and stored data remain available
under their existing controls.

The updated backend feature/catalog suite passed 22 mocked tests before the final
repository flag addition. TypeScript and focused catalog/settings lint passed.
Live UI, real AI generation and real Mongo mutation flows were not verified here.

### Environment credential security preparation, 2026-11-10

Environment writes now encrypt passwords and authorization tokens using AES-GCM,
with project/environment identity authenticated by the envelope. Public read/write
responses contain blank passwords and null tokens with configured markers. Read
responses never decrypt envelopes. Saved usernames/roles/non-secret notes remain
project metadata. Notes and variables are not secret storage.

Blank password inputs preserve the prior credential by stable identity. A username
change with a saved password requires re-entry. Removing a row revokes that role;
removing a saved token or selecting no authorization clears the token. Environment
revision checks reject stale edits. The encrypted bundle and metadata are updated
in one Mongo document, so no separate secret insert/cleanup can orphan credentials.
Delete removes that environment's bundle. The scoped runtime resolver is an
internal function and has no public secret-reveal endpoint.

Existing plaintext environment records are masked immediately in API responses and
converted on the next authorized save. No bulk migration or scan of saved credential
values was performed. Existing historical records/jobs, backups, notes and variables
are not retroactively scrubbed by this change. Legacy native execution rejects an
environment containing protected secrets instead of copying them into a job.
The approved synthetic adapter remains sample-only and does not retrieve credentials.

Local configuration was checked only for key presence and valid 32-byte decoding.
The key value was never printed. Use ENVIRONMENT_SECRET_MASTER_KEY or the existing
LLM_SECRET_MASTER_KEY fallback; preserve that key across restarts and deployments.
This is a versioned envelope with one configured key, not an implemented key-rotation
system. A dedicated key cannot be switched in after use without migration planning.

Verification uses synthetic in-memory database doubles and test keys. Eight focused
storage/security tests passed before the final compatibility run. Real MongoDB,
real onboarding/browser UI, Salesforce, evidence redaction and live cancellation
for a credentialed login have not been verified. See the ordered staging preparation
section in IMPLEMENTATION_PLAN.md for the next task and remaining gates.

Final credential-step checks passed 8 focused secret tests and 23 existing
feature/history tests with doubles, TypeScript, focused environment/onboarding
ESLint and git diff --check. The valid configured local key was reused through
settings without printing or replacing it. No commit/push was performed in this step.

### Staging binding Step 2, 2026-11-10

The local project overview now has a Staging login preparation section after
selecting an approved test case. Save the selected environment with encrypted
credentials, choose its application role, preview the binding, and save it. Refresh
restores the latest binding and validates its current inputs. A stale snapshot
requires a new preview/save. Bindings contain execution_ready=false and never start
a browser. The synthetic run controls continue to target only the controlled sample.

The binding pins canonical Salesforce Sandbox URL/origin, environment revision and
keyed digest, role/credential identity, approved test version/content and source
digests, and a preparation policy. Current approval versions still use the existing
synthetic approval schema. Full login-step approval is Step 3, not implemented by
this binding. Domain validation does not establish network/redirect/egress safety.
See EXECUTION_CONTRACTS.md for endpoints, immutable/idempotent semantics and limits.

Final checks passed 13 approved-run/binding ASGI tests and 8 credential tests using
synthetic auth/database doubles, TypeScript, focused lint and git diff --check.
No live UI/Mongo, Salesforce, real provider or distributed concurrency verification
was performed. Existing synthetic success/cancellation/evidence checks are mocked
within that suite. No credentials were resolved for binding preparation and no
commit or push was performed.

### General Step 3 authoring slice, 2026-11-10

Reusable workflows are optional and login is user-authored when needed. The local
Test Cases tab now has a reusable library and per-case approved specification
editor/preview. See APPROVED_WORKFLOWS.md for scope, APIs, versioning, UI steps and
verification. Eight new mocked authoring/compilation tests and 44 existing regression
tests passed, together with TypeScript, focused lint and diff checks. General browser
execution is not implemented by this slice, so Step 3 is only partially complete.
No new browser/AI/real-Mongo test or production deployment was performed.
