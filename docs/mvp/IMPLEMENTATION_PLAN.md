# Incremental implementation plan

Current priority (2026-11-13): qualify navigation performance before further product
features. See [PERFORMANCE_ASSESSMENT](PERFORMANCE_ASSESSMENT.md) for shared-client
fixes, first-request API latency, startup diagnostics and remaining signed-in checks.

Planning baseline: 2026-10-31, `dev` at `2479de4017cd8e29516daa1ecf62d5763bc2b6b2`. Target: [MVP_SPEC](MVP_SPEC.md). Evidence/feature treatment: [REPO_GAP_ANALYSIS](REPO_GAP_ANALYSIS.md). Constraints and experiments: [DECISIONS](DECISIONS.md). The original assessment was documentation-only; subsequent explicit tasks authorized integrated M1A and stabilization. [Current M1A evidence](M1A_DEVELOPMENT_SLICE.md#stabilization-and-real-development-verification-2026-10-31) records real integration with cached CfT but failed fresh-install startup. **Current accepted task direction (2026-11-03): record and then implement a bounded Linux-only M1B experiment alongside open Windows and Linux five-way reliability work. Retain the five-slot target/default and one-container-per-check topology. Latest independent Linux evidence is 4/5 workflow completions after 5/5 preparations; the successful parallel two-check UI run is user-reported. See DECISIONS A14 and the current task below.** Full M1 remains incomplete; historical estimates are not a delivery commitment.

## Next delivery sequence — one approved test and one environment

Work through these tasks in order and record the evidence at each exit gate.
The reported BrowserStack button click used a fixture-specific color/shape
detector and model label confirmation. Use one session for this sequence. Windows
fresh-install and five-way Linux reliability remain open, with five Linux slots
retained as the MVP target.

| Task | Deliverable | Exit gate |
|---|---|---|
| 1. Define the run contract | Map onboarding environments and story-generated cases to an explicit versioned run request. **Design complete.** | Document request, approval and immutable inputs, authorized access, result semantics and failure cases. See [approved visual run contract](EXECUTION_CONTRACTS.md#approved-visual-run-contract-design). |
| 2. Implement the approval snapshot and synthetic admission | Default-off, project-scoped approval/version persistence and synthetic admission are implemented. The admission record has no execution consumer. | An authorized reviewer can approve an exact specification. Missing approvals, missing expectations, stale revisions and foreign IDs reject before admission. Identical idempotent requests return the original run. |
| 3. Wire the existing test case UI | The project overview uses the existing case/environment lists and adds approval, preview, admission, status and cancellation. BrowserStack CI diagnostics are manual-only in this revision. | An administrator can approve. A project member can preview, admit, reload and cancel the admission. The preview identifies the controlled sample. The panel distinguishes admission from execution. |
| 4. Execute one approved synthetic sequence | Default-off UI start, one BrowserStack session, synthetic screenshot template matching, independent exact text comparison and project-scoped evidence. | Demonstrate correct expected text, reliable contradiction, ambiguous target, unavailable assertion evidence, cancellation, and no repeat click after uncertain submission. Live UI-to-BrowserStack verification is pending. |
| 5. Qualify and enable one staging environment | Add trusted origin/egress enforcement and explicit authorization for the staging target, actions and evidence processors. Use synthetic data and no login secrets. | Block off-origin redirects and resources, private/internal destinations and metadata access. Confirm provider/data approval, then run one reviewed non-consequential staging case. |
| 6. Return to reliability and concurrency | Qualify the dedicated Linux VM and isolated check containers. | Verify one sandboxed run, then two and five genuinely overlapping checks with independent evidence, cancellation, budgets and cleanup. |

Task 2 passed six ASGI tests with database and authentication doubles, plus
14 feature-policy and 21 batch regression tests. Live Mongo and browser
execution were outside that slice. Task 4 now has a local execution consumer.
Use the [Task 4 UI instructions](EXECUTION_CONTRACTS.md#task-4-single-session-development-execution)
for live verification before staging qualification.
The existing Visual Lab and story generation remain available throughout.

For local story-to-test setup, enable `FEATURES__STORY_MANAGEMENT`,
`FEATURES__SCENARIO_GENERATION` and `FEATURES__TEST_GENERATION`. Open a project
story with acceptance criteria, add or generate a scenario, review its steps,
approve it and generate a basic case. Return to Project Overview to select it
for a separate visual specification approval. The manual scenario path uses no
model calls. Reproduce Bug is hidden by default and can be restored with
`FEATURES__BUG_REPRODUCTION_UI=true`. This UI flag leaves the existing bug API
authorization and metering in place.

## Current bounded Linux M1B task (accepted 2026-11-03)

This scope amendment supersedes the earlier blanket M1B gate for a synthetic Linux
experiment only. Windows fresh-install and Linux five-way reliability stay open;
customer/production/cloud gates remain. Five active Linux checks remain the MVP
and configurable development target. Functional experiments can use one case to
isolate behavior without changing that capacity or declaring it qualified.

1. **Recommended first implementation task:** define the bounded screenshot/target
   proposal contract, use the existing managed AI gateway/control boundary, and
   identify/click one visible synthetic button through trusted Robot/direct-WebDriver
   actions. Pin screenshot identity, viewport/coordinate mapping and model/prompt
   identity; reject unknown/ambiguous/out-of-bounds or stale proposals. No DOM/JS or
   fixture-coordinate substitute for visual targeting. Acceptance: supported button
   located from the actual screenshot, allowed click observed, ambiguity safely
   stops, cancellation/action/model bounds enforced, evidence and latency retained.
2. Add bounded loading waits and incremental scrolling, with fresh observations
   after navigation/scroll/layout changes and detection of no progress. Acceptance:
   a delayed/off-screen target can be found; deadline/scroll/observation exhaustion
   stops safely; no guessed clicks or stale coordinates.
3. Add independent evaluation of approved text/numeric expectations. Acceptance:
   correct expectation is evaluated, deliberately wrong expectation fails,
   unavailable/ambiguous evidence cannot pass, and action success alone cannot pass.
4. Implement temporary-observation/selective-evidence handling, memory/image limits,
   retained assertion/checkpoint/failure images, deletion and measured capture/model/
   action/persistence latency. Keep required evidence before publishing an outcome.
5. Continue Linux five-way startup/cancellation/recovery qualification and the
   Windows diagnosis as separate reliability work. Retain failed denominators;
   qualify five overlapping sessions after an evidence-supported candidate fix.
   Neither two-check success nor M1B functionality closes these issues.

Prerequisites for the implementation task: configured supported vision provider,
scoped platform secrets, explicit experiment spending/model/action/time bounds and
reviewed synthetic expectations. Provider/model choice and capability validation
remain implementation work, not implicit approval of arbitrary endpoints or paid
calls in this documentation task. No customer data or production credentials.

No application implementation, feature enablement, model calls, browser executions
or infrastructure changes are performed by this scope-recording task. Next explicit
implementation request should start with item 1. Existing larger M1B/overall effort
ranges remain unvalidated; re-estimate after the visible-button and latency proof.


## Agreed product workflow (2026-10-31)

Train product knowledge → review/clarify and approve knowledge → add story + acceptance criteria → generate/review/approve tests → execute → review evidence → approve corrections when needed.

Recordings supply product knowledge; stories and acceptance criteria define test intent and expectations. Retain and adapt story-based Test Generation as the primary specification workflow. Flag conflicts with approved knowledge before generation; unresolved material conflicts block generation until reviewed. Every test version links to its story, specific acceptance criteria and approved knowledge version. Explicit approved expected results are required before execution. Corrections create reviewed successor versions, flag affected tests and preserve prior approvals and historical run references. Teach-back is optional within knowledge review; any browser demonstration still requires approved bounded actions and expectations.

The original workflow refinements were documentation-only. The current Linux M1B amendment above now permits its bounded experiment while the Windows qualification issue remains open. Existing effort ranges remain preliminary and have not been re-estimated for bounded parallel execution.

## Historical parallel scope (2026-11-02; superseded by A13/current five-slot design)

Two concurrent isolated batch containers are required for the MVP/demo, with
1-10 approved cases executed sequentially per container; additional batches queue.
This assigns up to 20 cases while keeping at most two cases/browser sessions active. This replaces the original one-browser target. Scheduling and
high concurrency remain deferred. Existing singleton API/OS locks and sequential
Linux evidence remain unchanged; no code or configuration is authorized by this
recording task. Do not activate legacy parallel execution as a shortcut.

Prioritized integration work (future, separately scoped):
1. Design Linux adapter dispatch through the existing authorized API with durable
   run/container identity, versioned manifests, private artifacts and cancellation.
2. Define atomic slot ownership across global/account/project/environment limits,
   fair durable queueing, spending reservations and conflict/dependency locks. Start
   with a global ceiling of two, with lower scoped caps where appropriate. Separate
   one-run idempotency from capacity allocation; use per-run process isolation and
   a scoped migration of singleton guards, not unguarded removal.
3. Implement independent status/evidence/cancel and safe crash reconciliation;
   preserve legacy execution records/APIs and separate consumers. Never reclaim an
   expired slot while its old job can still perform actions. Never replay an
   uncertain submit to recover capacity.
4. Demonstrate two overlapping synthetic jobs, third-run queue progression, repeated
   duplicate-start races, independent cancellation/failure, conflict serialization,
   cross-project denial and resource/spending ceilings. Measure actual overlap and
   per-job cleanup/evidence, not just multiple accepted requests. Then integrate
   approved real assertions and pilot qualification under the existing gates.

Dependencies: Linux dispatch contract and durable ownership design before concurrency
implementation; approved independent test data before customer parallel runs; cloud
sandbox/resource/network validation before cloud claims. Existing M1B/Windows and
customer-access security gates remain. Current effort ranges predate this addition:
re-estimate queue/slot/UI/reconciliation qualification after the design rather than
silently claiming parallel execution fits the previous 32-52 EW estimate.

## Historical sequential batch refinement (2026-11-02; superseded by A13)

Implement only under a separately scoped integration task. Extend dispatch design
with a batch manifest and distinct case-run identities; do not reinterpret legacy
batch fields as already supporting the new visual adapter. Batch membership is
one project/environment with exact approved case versions. Preserve legacy single-
execution responses and history; expose case-level outcomes/evidence and a separate
aggregate summary with partial/not-executed cases.

Add sequential case preparation, fresh browser/profile creation, bounded execution,
case evidence persistence and cleanup inside each container. Keep one active browser
session per container; atomically allocate two batch slots globally, scoped caps,
fair queueing and shared-data/dependency locks. Persist completed case results before
starting the next. Define measured case and whole-batch budgets; the existing smoke
90-second timeout is not a 10-case budget and is unchanged in this recording task.

Acceptance adds: 1 and 10-case boundaries; reject empty/oversize/mixed-scope batches;
two multi-case containers overlap while cases within each never overlap; third batch
queues; no cookie leakage; independent failure continues only eligible cases;
missing prerequisites block dependents; cancellation preserves completed outcomes
and cancels remaining cases without affecting the other batch; crash retains partial
evidence and never replays completed/uncertain actions. Test budget exhaustion,
slot recovery, cross-project artifacts and legacy-history compatibility.

Implementation update: the subsequent explicit contracts/backend task delivered
and verified only the synthetic mechanical batching/concurrency subset; see
EXECUTION_CONTRACTS.md. Approved customer cases, batch UI, usage ledger and broader
fault qualification remain gaps. Existing effort ranges predate both additions and
need re-estimation; the scope amendment itself did not authorize deployment.

## Original M1 milestone and remaining proof

**M1: isolated Windows visual-execution proof against a controlled sample application.** First task: define a minimal approved-specification, bounded action-proposal and assertion-result contract, then drive one deterministic form workflow through Robot → custom Python library → HTTPX → ChromeDriver → matched Chrome for Testing. Keep it outside production API/worker paths; use synthetic data and no real credentials. Do not begin with video ingestion or connect the current secret-bearing Redis payload to a model.

Demonstrate screenshot targeting, click/type/dropdown/scroll navigation, post-action checkpoints, and independent positive/negative text/numeric assertions. Include a wrong expected value, unknown target, timeout after submit and cleanup on failure. No required assertion may be skipped into a pass. Confirm prohibited clients are absent from the complete isolated dependency graph; preserve old packages untouched. This experiment decides whether to fund the larger product workflow.

## Milestones and release gates

Effort units are engineer-weeks (EW), 35 focused engineering hours each, excluding holidays, customer review wait and procurement. Ranges include design, implementation, meaningful tests and integration within each workstream; they are planning judgments, not measured throughput. M1–M6 total core work approximately 32–52 EW; subtasks overlap and are not additional to their milestone range.

| Milestone / effort | Tasks and dependencies | Acceptance / gate |
| --- | --- | --- |
| M1 Local proof: 2–4 EW | Define bounded contracts; isolated Robot library/direct WebDriver client, screenshot-to-target proposal, trusted action dispatcher, assertions, cleanup and limits. Pin Chrome/driver and test provider vision path. Controlled app only. | Repeated representative sample flows in visible and separate headless sessions; negative expectation reliably fails, ambiguous evidence goes to review, action budget/cancel honored, dependency graph excludes prohibited clients. Record reliability/cost baseline rather than claiming generalized autonomy. |
| M2 Platform safety/contracts: 4–6 EW | After proof contract review: audit tenant-scoped endpoints (including testcase reads), credential-reference migration design, redact logs/history responses, approved spec/knowledge/run contracts, adapter dispatch and proposed gates. Diagnose isolated feature-test stall/reconcile environment reproducibility. | Cross-project/role tests pass; no actual secrets in API/queue/log/model; immutable approval transition rejects stale drafts; legacy reads/default flags preserved; dry-run migration/rollback reviewed. Own-app execution stays blocked until gate passes. |
| M3 Training and knowledge: 8–12 EW | Private upload/status, restricted FFmpeg/frame extraction, prerecorded STT, multimodal gateway operations, source-linked claims/rules/unknowns/questions, review/approve/version/diff and persistent corrections. Depends on M2 access/data contracts. | Up-to-30-minute representative recording stays within measured resources; source links align; malicious/invalid uploads contained; conflicting/unknown claims cannot autoapprove; correction persists across login sessions; deletion includes derived artifacts. |
| M4 Story-based test design: 5–8 EW | Retain/adapt story and acceptance-criteria generation; repair and validate legacy generator interfaces without coupling generation to Playwright execution. Check knowledge conflicts before generation; pin story/criteria/knowledge versions. Draft purpose/role/preconditions/data/NL/structured actions/assertions/cleanup/rule refs; review and immutable approval; rule/story-change invalidation; optional explanation and approved bounded demo within knowledge review. Depends on M3 semantics and M1 executor. | Unresolved material story/knowledge conflicts block generation; source/version links are mandatory for approval; human approves explicit expected results before execution; skipping teach-back does not block approval; every required assertion has approved basis; unresolved input blocks run; changed rule flags cases; teach-back cannot invent permissions or silently revise expected behavior. |
| M5 Reliable execution/evidence: 7–12 EW | Extend execution API behind adapter; separate legacy payload dispatch; Mongo outbox/lease/fencing/action checkpoints/cancel/reconcile; bounded atomic batch-container slots (ceiling two), sequential 1-10-case manifests, fresh case sessions, fair queueing, scoped caps and shared-data serialization; evidence upload/manifests/report; action/model/time/money budgets. Evolve M1 into production-safe runner, normalize outcomes without rewriting old results. | Duplicate/expired jobs cannot double-execute; crash/ambiguous submit never blind-resubmits; all five verdicts tested; missing assertion cannot pass; partial evidence visible; artifacts private/durable; cancellation and entitlement refund work. |
| M6 Linux/cloud/pilot qualification: 6–10 EW | WSL/Linux parity, minimal locked image/SBOM, GCP Cloud Run services/Jobs spike, IAM/Atlas/GCS/Secret Manager/egress, resource benchmark, canary/rollback, representative 10–20-case corpus and pilot UX. Begin Linux/cloud experiment soon after M1 in parallel with safe independent M2 work to expose blockers early. | Actual cloud headless job with approved network path, sandbox decision documented, OOM/shutdown/driver cleanup/upload failures reconciled. Reviewer can complete training-to-run SaaS flow without installing anything. Pilot reliability/cost/retention thresholds met; no required security findings unresolved. |
| M7 Controlled free demo: additional 2–4 EW | After core safety, controlled app UX, invites, one user/project, ten-minute upload, five cases/five runs, seven-day screenshot retention, no scheduling; atomic entitlement/refund. | Rejected/duplicate requests do not overgrant/overcharge; platform failure returns allowance; own-app path invite-only; limits and deletion verified. |
| M8 BYOK beta: additional 3–5 EW | Extend existing configuration UI/SecretStore/gateway with organization admin policy, supported model/provider capabilities, allowlisted endpoints, rotation/revocation and no fallback; multimodal task matrix. | Capability failure rejected before activation; revoked secret stops new use; no silent account/provider fallback; tenant/organization tests and usage policy documented. |

M1–M6 includes managed AI and internal metering, not generalized BYOK/free marketing launch. Earliest useful proof is M1. An earlier mechanical driver/screenshot smoke test can appear in the first week but is not a validated visual executor. Do not promise a paid pilot on the mechanical smoke test.

### Core workstream allocation

For staffing, group the same core work into: visual execution/protocol/assertions approximately 7–12 EW; training/media/knowledge 8–12 EW; UI/approval/test design/teach-back 5–8 EW; security/contracts/migration 4–6 EW; orchestration/cloud/evidence/qualification 8–14 EW. Total 32–52 EW. This allocation redistributes M1–M6 rather than adding another estimate. Cost telemetry and reliable outcomes cross these streams; do not treat them as optional polish.

Assume experienced Python/FastAPI, TypeScript, browser-protocol, cloud and applied vision engineers; reusable foundation remains operational; customer provides recordings, expected behavior and usable staging access; no custom widgets/MFA beyond the pilot envelope. A solo developer at 35 engineering hours/week needs roughly 8–13 months for managed core pilot (32–52 working weeks). A two-engineer team needs approximately 19–31 elapsed weeks (about 4.5–7.5 months), assuming one backend/execution/cloud lead and one frontend/knowledge/media lead, shared QA and timely reviews. Perfect 2x speedup is unrealistic due to contract/review gates and integration. Add external waiting time separately; at 20 focused hours/week solo, multiply working duration by about 1.75. Confidence: medium for foundation reuse, low-to-medium for whole pilot until M1 and cloud gates pass.

Free demo plus BYOK adds approximately 5–9 EW beyond core, or about 5–9 solo weeks / 3–6 elapsed team weeks when safely parallelized. These are not required to validate the fixed-scope paid pilot. Deferred capabilities are excluded; individually, a restricted scheduler might be 2–4 EW, another validated browser/OS combination 2–5 EW, and hosted/private-network runner integration 6–12+ EW. These are low-confidence discovery allowances, not commitments; live training/takeover, general MFA, high concurrency and arbitrary endpoints need separate design/spikes before responsible estimates.

Critical path: visual reliability/clean runtime → approved knowledge/test contracts and isolation → source-linked training/approval → story-based test specifications/assertions → durable safe execution → headless cloud/network qualification → pilot. Media/UX development can proceed after shared contracts while Linux/cloud risks are probed early. If M1 fails representative workflows or cloud isolation cannot be demonstrated, re-scope before building a broad training UI. Do not quietly switch back to Playwright/Selenium clients to conceal a failed architectural proof.

## Expected amount of change

Planning units are logical modules, user-facing views, endpoint operations and durable record types—not files or lines. A module may span several files; counts overlap when one API supports multiple screens. Revise after contract design.

| Area | Changed/reused | New | Assumptions |
| --- | --- | --- | --- |
| Backend modules | ~8–12: auth/authorization, environments/secrets, execution service/queue/worker, result models, AI gateway/providers/usage/prompts, plans/index setup | ~10–16: media processing, transcription/frames, knowledge/questions/review/versioning, test-spec governance, visual library/WebDriver, assertions, artifacts, dispatch/leases/reconciliation, budget/deletion services | Existing registry/scanners and bug interpreter mostly preserved, not expanded. |
| UI views | ~4–7: project home/navigation, onboarding, environment/AI settings, usage/history | ~6–9: upload/library/status, source viewer, knowledge review/questions/diff, teach-back, test review/approval, run/evidence report | Some can be tabs/combined views; no demand for separate pages per concept. |
| API operations | ~10–18 changed/hardened around authorization, environment, execution/history, AI/limits | ~20–35 upload/status, knowledge/review/questions, test/version approval, demonstration, run/cancel/evidence/delete operations | Operations != routers; preserve old signatures or version explicitly. |
| Durable record types | ~4–7 extended: environments, executions, subscriptions/usage, configuration/prompt metadata | ~5–8 logical types: media/source, knowledge versions, clarification/review, test-spec versions, artifact manifests, dispatch/lease/action journal | Collections vs embedded docs decided by size/concurrency. No parallel duplicate test registry required. |
| Integrations | Extend existing Mongo/Redis/provider/SecretStore boundaries | ~5–7 groups: STT, frame/OCR tools, direct WebDriver/browser pair, private GCS, Cloud Run Jobs, cloud IAM/secrets/images | Grouping cloud services differently changes count; not a reuse percentage. |

## Additive migration and compatibility plan

1. Baseline inventories and backups using explicitly authorized non-production copies first; record schema versions, collection counts and caller/job ownership without logging secret values. Do not infer live usage from source. Define restore/rollback and legal retention obligations before modifying data.
2. Define versioned knowledge/spec/run contracts. Keep old `testcases` (code/locator fields), scenarios/stories/recordings and registry intact; identify legacy mode explicitly. Add compatibility reads for missing fields; never stamp old boolean approvals as new approvals or empty assertions as passed.
3. Harden project membership across all legacy reads/writes and references. Produce dry-run ownership anomalies; backfill only unambiguous creator ownership using existing membership pattern. Preserve project/user/environment IDs and usage/billing-owner associations.
4. Implement reference-only environment secrets with a replaceable store. Migrate credentials and redact old execution/history responses/log paths deliberately; handle queued old secret payloads via reviewed drain/quarantine/conversion, never accidental execution or blanket queue deletion. Old encrypted BYOK refs need store migration/rotation plans before changing backend.
5. Introduce RunnerAdapter registry and versioned new job envelope. Legacy Playwright stays explicit and retains current default-off gates. Visual worker receives only new approved refs; prevent legacy worker consuming visual jobs with separate queue/dispatch identity. Add outbox/idempotency and lease recovery rather than replacing all Redis users.
6. Import legacy stories/scenarios/cases only as source-linked drafts upon user choice. Flag unsupported locators/custom code and missing assertions; require review for visual equivalent. Preserve exports and original source metadata; no generated coverage claims.
7. Roll out in controlled sample → internal flag → invited staging pilot. Compare old history reads, membership, quota and UI gating regressions. On rollback, stop new dispatch and reconcile active runs; retain new immutable versions/artifacts so old code need not parse new writes. Avoid destructive schema downgrade.

Backfills required before general rollout: credential references/redaction, ambiguous ownership resolution, new manifests only for new runs, entitlement policy/configuration, lifecycle metadata for newly ingested assets. Legacy source import is optional and cannot establish missing evidence. Any immutable version storage must use atomic publication; existing registry delete/insert rescan is not that pattern.

## UI simplification, flags and deprecation prerequisites

M1A implements a separate default-off `visual_runner_lab` development gate. Full product gates such as `training_ingestion`, `knowledge_review`, `visual_execution`, and an invite/evaluation entitlement remain proposals whose names depend on contracts. API/write/job/model-use gates must reject before side effects; worker dispatch must independently validate mode/approval/version; UI must handle disabled features. New visual execution must not require enabling all legacy Story/Scenario/Recorder flags or reviving old queue consumption. Preserve `/features` behavior and regression tests. Configuration booleans do not substitute for tenant-level entitlements or readiness checks.

Retain story-based Test Generation in the primary MVP UI and adapt existing story/scenario review components; do not hide the story entry point. Reuse project onboarding and environment settings, while keeping account setup distinct from product training. The legacy DOM recorder, repository import and reproduce navigation may be optional or hidden through an explicitly scoped later UI change, preserving routes/data and feature controls. Generation must remain separate from execution; do not wire onboarding URLs or generated cases to the fixed M1A smoke specification. No flag changes are authorized by this plan. Keep history and environments accessible. Remove misleading sample metrics only when connected to real telemetry. Disable neither APIs nor workers merely because a screen is hidden.

Before removing any feature: identify live callers/users/jobs through an authorized inventory, map collections/references and exports, provide replacement or archive access, verify quota/permission effects, publish migration/rollback plan and obtain feature-specific scope approval. Comment-only code generation, unused broad packages, dormant export routes and mock charts are candidates for analysis—not authorized removals. Retain static scanners and discovery records without investing in new framework execution adapters.

## Verification strategy and readiness evidence

Use isolated fixture/unit tests for contracts, approval transitions, project access, prompts, limits and deterministic assertion comparisons. Use local HTTP/mock WebDriver tests for bounded protocol error handling; actual controlled-browser integration tests for trusted actions, coordinate/frame freshness, checkpoints, forbidden action rejection and cleanup. A deterministic mock cannot establish vision reliability.

Build a versioned pilot corpus with positive/negative expectations, alternate roles, UI ambiguity and unsupported widgets. Review false-pass/false-fail/needs-review rates, assertion coverage, model calls/latency/cost and reviewer corrections. Validate malicious source instructions, wrong-tenant refs, private artifact access, network restrictions and secret masking. Crash/retry/duplicate/cancel scenarios are release gates, including timeout after a consequential action and storage upload failure.

Run WSL/Linux and actual GCP headless qualification using pinned browser/image versions. Canary upgrades with rollback; measure memory/CPU and enforce operational limits. Confirm deletion for original recordings, frames, transcripts, vectors, screenshots, logs and backups per approved policy. Generate dependency/license notices from the resolved runtime, not a hand-written list. No production trial, full billing or public unrestricted evaluation is required to qualify the pilot.

Resumed diagnosis checkpoint (2026-10-31): fresh headless/headed and relocated-payload probes still fail, while the cached comparison completes. All 308 common payload files match by SHA-256; no cause or justified code fix was identified. The next prerequisite is an elevated, narrowly filtered native trace; this session lacks Process Monitor/native debugger and an elevated administrator token. See [current diagnostic evidence and manual next action](M1A_DEVELOPMENT_SLICE.md#resumed-startup-diagnosis-2026-10-31). Full 10/5 and real integration were not rerun; M1B stays deferred.

Diagnostic-bundle implementation checkpoint (2026-10-31): additive safe Lab observations and UI expansion are implemented and tested; fresh browser/driver remain running at timeout with no DevTools port/session. Two fresh headless probes failed, one cached comparison completed. No startup cause/fix or clean-install readiness is established. [Current diagnostics, checks and boundaries](M1A_DEVELOPMENT_SLICE.md#bounded-startup-diagnostic-bundle-2026-10-31). Next remains scoped native tracing, then a demonstrated fix and full fresh baseline/integration; M1B stays deferred.

Stable-version experiment checkpoint (2026-11-02): separate matched 156.0.8078.80 setup passed, but actual headless and headed checks failed 0/1 each at session handshake; old 146 control passed 1/1. No default promotion or full baseline is justified. Native trace remains unavailable in this non-admin session. See [complete experiment](M1A_DEVELOPMENT_SLICE.md#matched-stable-156-experiment-completed-on-resume-2026-11-02). M1B stays deferred.

## Next bounded task: Linux image execution (2026-11-02)

Image source and standalone launcher now exist; actual build/execution remain blocked
by no Docker/Podman engine or installed WSL distribution on this workstation.
Follow `visual-runner/linux/README.md`: build Linux/amd64, retain image ID and build
log, run one network-isolated headless synthetic smoke, inspect three PNGs/status,
then separate cancel, timeout and forced-stop checks. Keep sandbox enabled and
preserve first-attempt failures. Do not connect the container to existing API jobs,
Mongo or legacy consumers in this task. Do not claim Windows fixed or M1A qualified.
After successful local Linux gates, scope a development-only GCP feasibility job
with private artifacts, explicit resources and approved project. Deployment, durable
artifact upload, leases and cloud reconciliation remain separate unimplemented work.


Linux verification update (2026-11-02): local image built; agent baseline 3/3
completed and forced-stop/diagnostic timeout behaved as expected. See M1A evidence
and Linux README. The outer-watchdog and opt-in local stale-state reconciliation checks are now
verified; next bounded work is Linux dispatch design. GCP feasibility may be
scoped separately; local results do not establish cloud safety. No M1B.


Linux guard gate completed (2026-11-02): real force-kill reconciliation,
100s+10s parent watchdog with frozen child, and completed-record preservation
passed one attempt each. Opt-in controller only; do not equate it with automatic
Mongo/lease reconciliation. Next bounded task: design Linux adapter dispatch
through the existing authorized API while retaining Windows and legacy history;
settle container-engine ownership, durable run/container identity, cancellation,
private artifact transfer and restart reconciliation before implementing dispatch.
Keep Linux network sample-only and prohibit legacy queue consumers. Separately
scope GCP feasibility; no cloud deployment or M1B is authorized by this plan.


## Synthetic contracts/backend task completed (2026-11-02)

Implemented the bounded mechanical subset described in EXECUTION_CONTRACTS.md:
canonical/exported schemas, authorized default-off batch routes, durable Mongo queue/
two slots, pinned local Podman adapter, sequential cases and evidence/cancel/reconcile.
Full real-service post-fix and final focused fixtures passed 10 checks each; the full
fixture completed the ten-case boundary. Auth is a double, not real login/UI. Failure
history and remaining gates are in M1A notes. Existing legacy records/usage untouched.
Next: scoped batch UI with normal dev authentication, then batch-specific API process
restart/kill and DB/engine fault tests, scoped usage ledger and pilot contracts.
Do not mark account budgets/customer conflict locks/production fencing implemented.


Batch UI update (2026-11-02): synthetic controls/history/cancel/private evidence are
implemented in the existing Lab; types are generated from canonical models. Nine
intercepted UI checks and ten contract/API checks passed; see M1A evidence for initial
fixture/assertion failures and final static results. Existing real backend evidence
remains separate. Next: qualify normal development login through UI/API/TLS Mongo/
Podman, then batch process/engine failure coverage. Customer URLs, approved business
specifications/assertions, entitlement ledger and cloud remain separately gated.


## Per-check parallel dispatch — revised MVP scope (2026-11-02)

Supersedes the earlier two sequential batch-container topology. Batches group up
to ten cases; each active case owns an isolated container and durable slot. The
shared development pool defaults to five, with configurable global/account/project
caps. Two batches share that pool; ten simultaneous checks require separate capacity
qualification. Concurrency and chargeable execution allowances remain distinct.

Implementation task: canonical strategy/one-case dispatch identity, insert-only child
materialization, per-check Mongo ownership/reconciliation, independent containers,
parent aggregation/cancellation, legacy draining and compatible private artifacts.
Reuse the immutable one-case v1 runner protocol rather than introduce another stack.
Keep existing sequential records/manifests unchanged; no migration/backfill or legacy
consumer changes. New additive visual_batch_checks and host-bound check-pool ledger.

Acceptance gates: five established browser sessions observed together in one batch,
fifteen private screenshots and five first-attempt completions; shared-capacity/
idempotency races; cancellation of active/queued cases; restart without replay;
feature-off cleanup; fair progress; lower-cap recovery; project artifact authorization.
Record failures separately. No normal-login, multi-host or production claim follows
from private TLS Mongo/Podman/ASGI tests using authentication doubles.

Current qualification and exact commands are in EXECUTION_CONTRACTS.md and M1A.
Five-browser qualification remains open without deadline inflation or automatic
retries, as does normal development-login UI qualification. The bounded Linux M1B
experiment may proceed in parallel under A14. Customer URLs, shared-data locks,
entitlement ledger and cloud remain separately gated.


## Preparation investigation checkpoint (2026-11-03)

Completed: typed durable stage/reason/timing metadata, preservation of original
engine error through reconciliation/parent cases, UI preparation timeline, fault
injection and focused regressions. Historical pre-start failure not reproduced;
its cause is still unknown. Actual preparation passed all five concurrent checks;
4/5 workflows completed and a later browser session was rejected. Two one-case
controls completed, three private artifacts/cross-project denial and five-case
cancellation/PID0/slot release passed in private Mongo/Podman fixtures with auth
doubles. See M1A for exact evidence and commands. Next task is a separately scoped
diagnosis of the explicit session-not-created response under five-way load, then
qualification after a candidate fix. No more blanket five-check reruns. That
preparation task did not implement M1B; the current A14 experiment may now proceed.

## Staging login preparation — ordered work, 2026-11-10

The user selected Salesforce Sandbox (`https://test.salesforce.com`) and requested
these tasks one at a time before returning to browser-hosting arrangements.

1. **Secure environment credentials — implemented locally.** AES-GCM-encrypted
   passwords/auth tokens are stored in the environment document. Read responses
   redact existing and new secrets, blank edits preserve saved values, revisions
   reject stale writes, and validation errors omit submitted values. Username,
   role and non-secret notes remain authorized project metadata. Legacy plaintext
   records are encrypted when saved, without a bulk migration. A trusted,
   project-authorized runtime resolver exists but is not connected to execution.
2. **Pin URL, application role and approved test version — binding-only preparation implemented locally.**
   Bind exact environment revision, credential identity, target policy and approved
   specification before dispatch. Reject stale admission and role changes. Keep
   secret values out of manifests, model requests, logs and persisted results.
3. **One bounded staging login workflow — pending.** Specify approved login actions
   and explicit success/failure observations, including authorized redirects.
   Browser hosting and vision-processing decisions remain pending; the existing
   synthetic adapter does not navigate Salesforce or resolve environment secrets.
4. **Cancellation, redaction and failure qualification — pending.** Verify expected
   and negative outcomes, uncertain submission without replay, cancellation/cleanup,
   screenshot redaction and unauthorized evidence access against approved synthetic
   staging fixtures before using customer credentials.

The dedicated optional ENVIRONMENT_SECRET_MASTER_KEY is preferred. Where absent,
this implementation reuses the configured LLM_SECRET_MASTER_KEY. The selected key
must remain stable and backed up. Adding/changing a dedicated key after envelopes
exist requires an explicit rotation/migration plan. No automatic key rotation,
production migration, real Salesforce login or third-party credential delivery has
been performed. Legacy execution rejects protected environments before persistence,
because its old job format copies credential values and cannot safely consume them.

Step 2 update, 2026-11-10: the non-executable staging binding API/UI is implemented
locally. It records URL/origin, target policy, environment revision/digest, application
role/credential identity and exact approved version/source digests. Refresh restores
and revalidates the latest immutable binding. See EXECUTION_CONTRACTS.md staging
binding v1 for limits and routes. This is not the future login-step approval schema;
existing approved versions still describe the synthetic sequence. Step 3 must define
and review login actions and expectations before any adapter may consume the binding.


## Step 3 scope amendment, 2026-11-10

General approved specifications with optional reusable workflows supersede a
mandatory Salesforce-login stage. Users choose inline actions and linked exact
workflow versions. Public cases need no role; credential steps select a saved
application role. [Approved workflows](APPROVED_WORKFLOWS.md) documents the local
flagged authoring, approval, compilation/preview and dependency-review implementation.
General browser execution remains pending interpreter, hosting/vision permissions,
target/network enforcement and real-service qualification. Step 3 is therefore
partially implemented; authoring approval is not execution readiness.

## Knowledge-first implementation and execution sequence, 2026-11-11

Continuation: durable readiness dispatch and a separate worker/Robot child are
implemented; [WORKFLOW_WORKER.md](WORKFLOW_WORKER.md) records real Mongo and bounded
BrowserStack evidence, cancellation fixes, and remaining gaps. General case actions
and assertions are still not executed. Next is the bounded visual action interpreter
(task 3), retaining network/credential gates and conservative outcomes.

The [knowledge slice](PRODUCT_KNOWLEDGE.md) implements default-off text/transcript
source review, immutable snapshots, story ambiguity/gap/conflict review, metered
context-aware design and requested/allowed/actual counts. Scenarios now represent
coverage intent; detailed testcase procedures/assertions follow approved intent.
Retain legacy records and flag-off behavior. No recording pipeline is delivered.

The user's seven next execution tasks, exact acceptance gates and unfinished work
are tracked in [approved execution delivery](APPROVED_EXECUTION_DELIVERY.md).
Durable compiled admission and a separately supervised Robot/direct-WebDriver
readiness worker are implemented. General actions/assertions and fail-closed
network/evidence controls remain unfinished. BrowserStack is the first accepted
development provider behind reusable interfaces. Do not
reinterpret existing synthetic jobs or attach to legacy consumers.

Real verification needs a dedicated authorized development project/environment and
provider screenshot permission. Do not merge on unit tests or service pings alone.
The bounded knowledge/admission and readiness slices were merged through PRs #1
and #2; that does not complete the seven gates or qualify the full MVP. Future
implementation follows the same `dev` → `main` review workflow without bypassing
required review. Existing Windows/five-way reliability issues remain open.

## Proposed hybrid targeting change — 2026-11-11

The user requested a plan before changing the screenshot-first approach. See
[HYBRID_EXECUTION_PLAN.md](HYBRID_EXECUTION_PLAN.md), the detailed source for this
proposed work. It replaces the **recommended next implementation task** above
with H0 (explicit policy/versioned-contract amendment) and H1 (direct-WebDriver
semantic capability proof), followed by semantic actions, independent assertions,
bounded visual fallback and security/UI/integration qualification.

This is planning only: no execution policy, feature flag, application behavior,
dependency or stored approval is changed. Semantic/accessibility/DOM operations
must be explicitly introduced during an assigned implementation task; do not
silently bypass the existing targeting constraint. Customers still write no
selectors. Preserve all current adapters, histories, isolation and no-replay rules.

Full bounded work is estimated at 19–33 engineer-days (4–7 weeks solo at 30 focused
hours/week), subject to provider, egress and redaction gates. This excludes the
rest of the MVP. The initial capability proof is 2–4 days after H0; measure actual
provider support and RPC overhead before expanding the implementation.


## Platform prompt phases (2026-11-11)

See [Platform prompts](PLATFORM_PROMPTS.md). Phase 1 connects knowledge extraction,
story analysis and knowledge-aware scenario/test design to the existing platform-only
registry. Phase 2 now migrates legacy dynamic templates without changing their contracts.
Phase 3 adds synthetic draft preview and real-login qualification. Execution stays
out of this work. Backend owner configuration reuses PLATFORM_OWNER_EMAIL.


UI/UX refresh (2026-11-12): shared controls and accessible onboarding/dialogs,
Test Design page hierarchy and platform prompt activation improvements are implemented for development.
See [scope, commands, evidence and remaining qualification](UI_UX_REFRESH.md).
Phase 3 synthetic preview and real-login/provider checks remain next; recording
ingestion is still gated on private storage. Do not resume Execution MVP by inference.


## Customer account foundation — current slice (2026-11-12)

Ownership/isolation implementation is default off: naming in existing onboarding, local/verified OAuth provisioning, account-admin invitations and same-account project access. [Customer accounts](CUSTOMER_ACCOUNTS.md) records migration, tests and release gates. Next: review explicit existing-user mappings, resolve cross-account legacy memberships, take backup/maintenance window, dry-run/apply/verify, then enable and qualify normal browser/OAuth login. Do not apply to existing data automatically. Following separately scoped phases move subscription/usage to the customer account and introduce account-local display numbering; preserve old identity/history links. Test Design remains the product priority; no execution scope advances here.


Account Team/shared billing amendment (2026-11-12): see [ACCOUNT_TEAM_BILLING.md](ACCOUNT_TEAM_BILLING.md). Account OWNER/ADMIN manages same-account project assignments centrally; project-content/evidence access still requires membership. `account_subscriptions` is default off; billing cutover is an explicit reviewed migration, after which the account subscription is canonical even if the flag is disabled. Preserve legacy user subscriptions and histories; do not silently reset usage or apply existing-data migration at startup. Account-local display IDs remain future work.


Account presentation/Free team amendment (2026-11-12): [ACCOUNT_UI_REFINEMENTS.md](ACCOUNT_UI_REFINEMENTS.md) records hidden account IDs, centralized workspace order, grouped testcase usage, two additional Free account members, optional SMTP delivery (disabled; manual links retained), and the relocated/default-hidden Test Execution page. Other quotas and execution qualification gates remain unchanged.

# Manual testing priority amendment — 2026-11-13

Current assigned slice: Test Cases/Scenarios tables, reusable final-result contract,
manual results and selected-case Test Execution with Release/Cycle notes. See
[MANUAL_TEST_EXECUTION](MANUAL_TEST_EXECUTION.md) for delivered boundaries, gates and
verification. Automation remains hidden/default-off. Next bounded task is reviewed
bug drafting/linking and its platform prompt; this task does not implement it.
Knowledge/story-analysis visibility and ingestion remain subsequent priorities.


### Account setup refinement (2026-11-13)

Optional reusable AI Setup in onboarding, Managed default, request labels and
zero/missing allowance presentation: see ACCOUNT_UI_REFINEMENTS.md. AI allowance
qualification and mode-switch commercial billing remain tracked, deferred work in
AI_ALLOWANCES_PRICING.md. Preserve all counters and current paid-entitlement limits.
