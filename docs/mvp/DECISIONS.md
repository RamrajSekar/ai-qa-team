# MVP decisions and validation register

Assessment date: 2026-10-31. [Scope](MVP_SPEC.md) governs this track. Accepted means a planning constraint from the user brief, not an implemented capability.

## Accepted constraints

| ID | Decision | Consequence |
| --- | --- | --- |
| A1 | Extend Next.js/TypeScript + FastAPI/Pydantic + MongoDB. | No stack rewrite. Preserve users, projects, environments, history, legacy tests and registry. |
| A2 | Recording-trained, approved visual testing is the current delivery target. | Earlier brownfield discovery/data roadmap is preserved as optional work, not a prerequisite. Existing repository safety rules still apply. |
| A3 | Robot + custom Python + direct WebDriver + ChromeDriver + Chrome for Testing. | No Selenium/Playwright/Puppeteer client dependency in the new isolated executor; keep old mode separately. |
| A4 | Specialized backend AI tasks; trusted deterministic policy code. | No arbitrary code execution, unrestricted Robot keywords, swarm or new agent framework. |
| A5 | Human approval, immutable versions, evidence-based verdicts. | Prompt versioning is a reuse pattern, not a substitute for product knowledge/test governance. |
| A6 | Mongo durable truth; Redis retained where useful. | Do not replace working rate limits or queue concepts merely for tidiness. Job correctness cannot depend on a destructive list pop. |
| A7 | Windows → WSL/Linux → GCP spike → SaaS pilot. | No cloud feasibility claim from local browser success. Current concurrency target is A13: five shared Linux check slots. A14 allows a bounded Linux M1B experiment while Windows/five-way reliability remain open. |
| A8 | Managed first, supported BYOK beta, controlled evaluation. | No unrestricted own-app browser service, arbitrary endpoint or finalized pricing promises. |
| A9 | Original assessment was documentation-only; subsequent explicit M1A implementation authorized. | Integrated default-off mechanical lab is scoped in M1A notes. No cloud deployment, commit, push, legacy enablement or broad migrations. |
| A10 | Recordings build knowledge; stories + acceptance criteria drive test specifications. | Retain/adapt story-based generation; approved knowledge supplies context. Block generation on unresolved material conflicts; link test versions to story/criteria/knowledge; require approved expected results before execution. Corrections are reviewed successor versions. Teach-back is optional within knowledge review. This is target scope, not a claim of delivered behavior. |
| A11 (historical; superseded by A13) | Bounded parallel execution is required for the MVP/demo (accepted 2026-11-02). | Initial global ceiling two isolated batch containers (refined by A12); additional batches queued; lower scoped caps, fair dispatch, atomic capacity/budgets and shared-data serialization. Supersedes one-browser target, not current implementation. No scheduling/high-concurrency promise or implementation authorization. |
| A12 (historical; superseded by A13) | One container per batch of 1-10 approved cases, executed sequentially (accepted 2026-11-02). | Two batch containers concurrently; at most two active cases/browser sessions globally. One project/environment per batch, fresh sessions for independent cases, pinned per-case versions/results/evidence, batch summary and case/batch budgets. Cancellation preserves completed cases and cancels pending cases; no batch replay after interruption. Target only, not implemented. |
| A13 | Parallel checks within/across batches, one container per active check; shared configurable Linux pool defaults to five (accepted 2026-11-02). | Supersedes A11/A12 topology and two-slot ceiling. Batches group 1-10 cases; excess checks queue under global/account/project limits. Preserve legacy records and ownership. Five-way reliability remains unqualified (latest measured 4/5 workflows); configured capacity is not proof. |
| A14 | Bounded Linux-only M1B experiment may proceed while Windows and Linux five-way reliability remain open (accepted 2026-11-03). | Five remains the MVP target/default; no reduction to two. User-reported two-check UI success is separate from independent qualification. Functional visual-target/assertion experiments may run alongside reliability work, with the sample-only security/control boundary intact. No customer/cloud/production readiness or completed M1A/M1B claim. |

## Proposed decisions requiring experiments

| ID | Proposal | Validation / decision gate |
| --- | --- | --- |
| P1 | Separate minimal visual-runner environment/image and adapter, sharing normalized execution API concepts. | M1A implements the separate local environment, fixed Robot smoke adapter and client-free graph. Approved-spec/assertion/AI targeting, images and release SBOM remain future gates. No eager legacy imports. |
| P2 | Cloud Run services for control plane and Jobs for media/execution; retain Redis for current coordination. | Benchmark actual Linux container, sandbox, fonts, viewport, OOM, job initiation, private staging path and cancellation. No deployment authorized by this audit. |
| P3 | Start browser sizing experiments around 2 vCPU / 4 GiB with one task; separate media job. | This is a benchmark starting point, not a minimum or capacity claim. Measure peak memory, CPU, screenshot latency and 30-minute media processing separately. |
| P4 | Private GCS artifacts, Mongo metadata, Secret Manager-backed runtime credentials. | Verify scoped signed access, deletion, interrupted uploads, IAM and database connectivity; retain replaceable SecretStore contract and migrate encrypted Mongo references explicitly. |
| P5 | FFmpeg/OpenCV frame sampling; evaluate OCR and prerecorded transcription. | Representative English recordings, timestamps, costs, numeric/text accuracy, sensitive data masking and codec/resource tests. Tesseract not mandatory until measured. |
| P6 | Reuse provider gateway/usage/prompt boundaries, extend multimodal contracts and cost reservations. | Existing text-only request is insufficient; test vision/transcription capabilities per allowed model and reject unsupported combinations. |
| P7 | Server-owned dispatch outbox, expiring Mongo lease/fencing, idempotent results and action checkpoints; zero automatic retries of whole browser jobs initially. | Simulate duplicate initiation, process loss, stale lease, ambiguous submit, cancellation and artifact failure. Do not mistake at-least-once delivery for exactly-once side effects. |
| P8 | Additive knowledge, specification, media and run-artifact records; retain legacy collections. | Contract review first; choose collections versus embedded versions by size/query/concurrency needs. No destructive backfill. |
| P9 | Reuse Pydantic feature system with separate training/knowledge/visual execution/evaluation entitlements. | M1A adds default-off development-only `visual_runner_lab`; full product gates remain proposals. API/process/UI guards remain independent of legacy native execution; preserve history. |

## Open questions and ownership

Stabilization decision (2026-10-31): **do not advance to M1B yet**. Real login/UI/API/TLS Mongo scenarios passed with an explicitly selected cached CfT installation, but the fresh bundle failed 0/10 headless and 0/5 headed first attempts after setup/OS-context corrections. Retain the historical pin for reproducibility; official feed lists a newer stable release, which was not adopted in this task. Fresh-vs-cached native Windows startup diagnosis remains unresolved. See [current results and exact blocker](M1A_DEVELOPMENT_SLICE.md#stabilization-and-real-development-verification-2026-10-31).

M1A uses a server-owned synthetic order form; recording-led priority is already accepted and needs no reconfirmation. Before M1B, select the approved positive/negative sample assertions and supported visual model/budgets. Pilot module/customer expectations remain a later customer gate.

Before own-app execution, product/security owners approve staging origins/network path, roles, allowed consequential actions, training consent, retention, redaction and deletion obligations. Identify whether application MFA can be excluded or requires a pre-provisioned supported session; general MFA remains deferred.

Before pilot commitments, product/QA owners set reliability targets, supported widget list, ambiguity escalation policy, cost ceiling and review turnaround. Validate workload on fixed corpus rather than choosing a success percentage without evidence. Cloud owner chooses region, IAM, Atlas connectivity and egress enforcement design based on the spike.

Before BYOK beta, decide organization/account ownership versus current project ADMIN scope, approved model/provider matrix and endpoint allowlist (existing Azure endpoint configuration is not permission for arbitrary URLs). Decide how managed budget reservations account for timeouts and BYOK still consumes platform allowance.

Before pricing, validate inference/transcription/storage/browser cost and operational support hours; pilot price is a commercial experiment, not evidence of engineering cost coverage.

## Deviations and source precedence

No deviation from requested target architecture is recommended. Reusing Redis and the existing encrypted secret abstraction is an incremental migration recommendation, not substitution for the target security controls. Existing Playwright/Selenium **static scanners** are implemented despite older prose saying future adapters; they are neither visual executors nor client-free runtime proof. Preserve them without expanding MVP scope.

Root AGENTS gives current source precedence. User-aligned root skill/context now govern the recording-led track; the earlier statement that they remained unchanged is historical. Preserve their mandatory safety rules and actual user edits. M1A's fixture coordinates are an explicitly authorized mechanical development exception, not a substitute for visual AI targeting in M1B. See [M1A evidence and limits](M1A_DEVELOPMENT_SLICE.md).

## External references checked for feasibility

Reviewed 2026-10-31; these describe platform constraints, not repository runtime validation:

- [Cloud Run container contract](https://docs.cloud.google.com/run/docs/container-contract): Linux container/runtime and ephemeral filesystem considerations.
- [Job creation](https://docs.cloud.google.com/run/docs/create-jobs), [execution](https://docs.cloud.google.com/run/docs/execute/jobs), [timeouts](https://docs.cloud.google.com/run/docs/configuring/task-timeout), [retries](https://docs.cloud.google.com/run/docs/configuring/max-retries), [memory](https://docs.cloud.google.com/run/docs/configuring/jobs/memory-limits): job lifecycle/resource controls require explicit configuration and tests.
- [ChromeDriver version selection](https://developer.chrome.com/docs/chromedriver/downloads/version-selection): select compatible browser/driver releases; pin both in a versioned image.

Resumed diagnosis checkpoint (2026-10-31): fresh headless/headed and relocated-payload probes still fail, while the cached comparison completes. All 308 common payload files match by SHA-256; no cause or justified code fix was identified. The next prerequisite is an elevated, narrowly filtered native trace; this session lacks Process Monitor/native debugger and an elevated administrator token. See [current diagnostic evidence and manual next action](M1A_DEVELOPMENT_SLICE.md#resumed-startup-diagnosis-2026-10-31). Full 10/5 and real integration were not rerun; M1B stays deferred.

Diagnostic-bundle implementation checkpoint (2026-10-31): additive safe Lab observations and UI expansion are implemented and tested; fresh browser/driver remain running at timeout with no DevTools port/session. Two fresh headless probes failed, one cached comparison completed. No startup cause/fix or clean-install readiness is established. [Current diagnostics, checks and boundaries](M1A_DEVELOPMENT_SLICE.md#bounded-startup-diagnostic-bundle-2026-10-31). Next remains scoped native tracing, then a demonstrated fix and full fresh baseline/integration; M1B stays deferred.

Stable-version experiment checkpoint (2026-11-02): separate matched 156.0.8078.80 setup passed, but actual headless and headed checks failed 0/1 each at session handshake; old 146 control passed 1/1. No default promotion or full baseline is justified. Native trace remains unavailable in this non-admin session. See [complete experiment](M1A_DEVELOPMENT_SLICE.md#matched-stable-156-experiment-completed-on-resume-2026-11-02). M1B stays deferred.

## Linux feasibility preparation — 2026-11-02

Accepted task scope: isolated container preparation for the same synthetic M1A
workflow, while preserving the unresolved Windows baseline. This is an OS-isolation
experiment, not a Windows fix or permission to start M1B. See
`visual-runner/linux/README.md`. No cloud resources were created. Linux process
groups supplement the container boundary; they do not establish Windows Job Object
parity or multi-host leases. Sandbox remains enabled; an incompatible host must fail
rather than receive a no-sandbox workaround. The image must be built/run and its
resolved dependencies, licenses, resource use and cleanup verified before promotion.


## Local Linux reconciliation boundary (2026-11-02)

Accepted for this synthetic spike: explicit stopped-container controller, original
image identity, dedicated output volume, terminal/idempotent state preservation,
no replay. Actual outer-watchdog fault injection passed at unchanged 100s+10s.
This is a single-operator local tool, not fencing against manual restarts or a
production reconciler. API/UI/Mongo integration and GCP remain separately scoped.
See M1A guard evidence. Windows startup diagnosis is still unresolved; no M1B.


## Implemented mechanical batch subset (2026-11-02)

Current explicit task authorized contracts/backend implementation: a separate
versioned mechanical fixture contract, generated runner schema, new default-off
batch flag/routes and durable local two-slot dispatch. See EXECUTION_CONTRACTS.md.
No inherited legacy batch/approval meaning. Image ID is developer-owned and immutable,
no caller URLs/code, no subscription charges, no real assertion verdict. Recovery
never starts an existing identity; missing post-start containers hold slots for
operator review. Single checkout/host only, not distributed fencing. Real-service
ASGI fixture passed with authentication doubles; normal UI/login is a next gate.


## Synthetic batch UI integration (2026-11-02)

The existing Visual Runner Lab now exposes the fixed batch APIs under both flags.
Pydantic also generates the UI types, checked for drift. Pending starts are scoped
to member/project and use explicit same-key resolution after network uncertainty;
no automatic POST or browser replay. Customer onboarding URLs and generated tests
are not accepted/executed. UI regressions are intercepted fixtures, distinct from
prior real Mongo/Podman backend evidence. Normal-login full-stack qualification is
still a separate gate. No subscription charging, M1B or deployment in this task.


## Accepted: parallel cases within batches (2026-11-02)

User explicitly superseded the earlier sequential-per-batch design. Batch is a
logical result group, not a container. One isolated container/browser per active
check; a shared configurable global pool defaults to five with account/project
caps. A five-case batch can use all five slots. Two batches share capacity rather
than multiplying it. Preserve the size-ten batch boundary and separate concurrency
from execution allowance. Synthetic runs remain unbilled.

Reuse the existing immutable v1 runner protocol with one case per container; add
private CheckDispatch identity validation and public execution_strategy/adapter
identity. Existing v1 sequential batches drain first and retain their original
records. A separate durable check ledger and visual_batch_checks collection are
additive. Preserve project authorization and existing evidence URLs. No image
rebuild, client-library fallback, M1B or customer URLs.

Five-browser capacity is a validation gate, not established by configuration. Local
Mongo/kernel-lock ownership is not multi-host fencing. Customer shared-data conflicts,
subscription accounting and real-login/cloud qualification remain unresolved gates.


## Preparation diagnostics and error provenance (2026-11-03)

Preserve original engine/preparation errors when reconciling interrupted jobs and
aggregating parents. Ordinary code persists fixed stage/reason enums, bounded
events/timings before commands. Progress persistence failure aborts preparation;
metadata waits are bounded without changing browser/CLI deadlines. API/UI receive
only typed summaries, never raw engine output/paths/arguments. No retroactive
invention of diagnostics for old records. This is an observability/reliability fix,
not evidence of a root-cause fix for historical preparation failure. One-case
controls pass; five-way browser qualification remains 4/5, not complete. Keep the
accepted Robot/direct-WebDriver architecture; no CDP or M1B implementation.


## A14 boundaries and rationale (2026-11-03)

The user accepted advancing a bounded Linux M1B experiment without lowering the
five-check Linux concurrency target or closing either reliability issue. This
supersedes earlier blanket M1B deferrals only for this synthetic Linux experiment.
Historical reports remain unchanged. Successful two-check execution is user-reported;
latest independent five-check evidence is 5/5 preparation and 4/5 completion with
one session-not-created response. Windows fresh-install baseline remains failed.

The experiment must demonstrate screenshot-derived targets, trusted allowlisted
actions, bounded wait/scroll with fresh observations after layout changes, explicit
independent assertions and safe ambiguity stops. Do not infer correctness from
navigation/action success. Temporary observations need not be durably retained;
keep required assertion/checkpoint/failure evidence with retention/deletion policy.
Measure capture, model, action and persistence latency; bound memory, image volume,
model calls, actions, retries and spending. Missing or ambiguous evidence cannot pass.

Keep the Robot/custom Python/direct HTTPX WebDriver/ChromeDriver/CfT architecture.
CDP remains an evaluated alternative, not an accepted implementation change. No
arbitrary model tools/code/Robot keywords/URLs, DOM/selector/JavaScript targeting,
customer credentials, production, deployment or autonomous corrections. Implementation
and any paid model experiment require an explicitly assigned task, configured
supported provider and trusted usage/secret controls. This update performs no such
execution. Qualification/security gates for customer and production use remain.


### 2026-11-10 — optional reusable workflows

Accepted user scope replaces mandatory application login with general approved
case steps and optional linked reusable versions. Login is a user-authored setup
when needed. Public-page cases may omit credentials. Saved environment URLs remain
subject to target/network authorization. The initial implementation is development
only authoring, immutable approvals, compilation and preview; browser runtime is
not enabled. See APPROVED_WORKFLOWS.md. No browser-host or image-processing decision
has been inferred from this scope amendment.

### 2026-11-11 — knowledge-first design and execution delivery

Accepted: approved product knowledge contextualizes story/acceptance-criteria-based
design. Scenarios are coverage intents, not duplicate detailed cases. Testcases
contain concrete procedures, explicit expectations/assertions, data and cleanup.
Material analysis findings require reviewed resolutions; changed context requires
renewed review. Requested generation counts may be capped or return fewer supported
distinct results and must report actual counts honestly.

Development choice: document text and timestamped transcript excerpts precede media
ingestion; they must not be advertised as uploaded-recording training. Knowledge/design
tasks extend the existing metered gateway. Multi-host approval/quota races, media
ingestion, retention and real provider integration remain unqualified.

BrowserStack is accepted as the first development execution provider behind a
reusable adapter, superseding its earlier deferred status for the user's assigned
execution tasks. Immutable general run admission remains non-executable until the
isolated worker, network/evidence controls and real checks are complete. See
PRODUCT_KNOWLEDGE.md and APPROVED_EXECUTION_DELIVERY.md. No production readiness,
automatic provider fallback or merge approval from test doubles is implied.

### Proposed: semantic-first hybrid targeting — 2026-11-11

The user requested a plan following architectural feedback. The recommendation is
semantic role/name/label/scoped text first, stable attribute contracts second,
and permissioned visual proposals for unsupported discovery cases. Unresolved
ambiguity stops safely. Vision is not a deterministic fallback; failing assertions
and uncertain actions must never trigger a more permissive execution strategy.

[HYBRID_EXECUTION_PLAN.md](HYBRID_EXECUTION_PLAN.md) defines the phased plan,
contract migration, provider capability proof, security/qualification gates and
effort assumptions. This entry records **planning**, not implemented capability or
blanket approval to alter runtime behavior. H0 must explicitly amend the earlier
vision-only constraint and version the resolution policy/contracts when an
implementation task is assigned. No old approved version is automatically converted.

Preserve Robot/custom Python/direct HTTPX WebDriver and dependency isolation.
Full accessibility-tree/CDP support through BrowserStack is an experiment, not a
prerequisite or guaranteed capability. Arbitrary JavaScript, generated selectors,
model code, unrestricted Robot keywords and uncertain-submit retries remain excluded.


## Platform prompt ownership (2026-11-11)

Shared task prompts are managed by platform OWNER/ADMIN, not project administrators.
Approved project knowledge is separate scoped memory, not model fine-tuning. Reuse
the existing registry/UI and backend PLATFORM_OWNER_EMAIL bootstrap. See
[implementation and remaining phases](PLATFORM_PROMPTS.md). Editable instructions
cannot replace code-enforced schemas, isolation, approvals or permissions.


## Customer accounts and onboarding (2026-11-12)

Accepted: one customer account per user, stable pending account at new signup/verified first OAuth; account name in existing Account & Project onboarding. Account OWNER/ADMIN manages customer invitations; project administrators assign existing same-account members. No platform/project role bypass, account switcher, implicit customer merger or account creation on normal login. Explicit reviewed existing-data migration precedes enabling the default-off feature. See [contracts and limits](CUSTOMER_ACCOUNTS.md). Billing/usage ownership and account-local display IDs remain separate work.


Account Team/shared billing amendment (2026-11-12): see [ACCOUNT_TEAM_BILLING.md](ACCOUNT_TEAM_BILLING.md). Account OWNER/ADMIN manages same-account project assignments centrally; project-content/evidence access still requires membership. `account_subscriptions` is default off; billing cutover is an explicit reviewed migration, after which the account subscription is canonical even if the flag is disabled. Preserve legacy user subscriptions and histories; do not silently reset usage or apply existing-data migration at startup. Account-local display IDs remain future work.


Account presentation/Free team amendment (2026-11-12): [ACCOUNT_UI_REFINEMENTS.md](ACCOUNT_UI_REFINEMENTS.md) records hidden account IDs, centralized workspace order, grouped testcase usage, two additional Free account members, optional SMTP delivery (disabled; manual links retained), and the relocated/default-hidden Test Execution page. Other quotas and execution qualification gates remain unchanged.
