# AGENTS.md — AI QA Squad

Approval usability amendment (2026-11-13): human-review supporting outcomes,
cleanup and source-rule/criterion selections are optional; per-step expected results
remain required. `test_design_admin_review` defaults false: authorized project
members can explicitly approve saved versions; true requires project ADMIN.
Persist the authenticated approver identity/name/role, time and policy immutably.
See `docs/mvp/MANUAL_TEST_EXECUTION.md`; do not weaken AI generation contracts or
silently auto-approve tests to satisfy optional fields.

Manual testing amendment (2026-11-13): see `docs/mvp/MANUAL_TEST_EXECUTION.md`.
Manual execution manifests and final results are separate from approved cases and
automation queues. Public manual input cannot choose an automated mode or verdict
source. A manual Passed report requires confirmation of all approved expectations.
Knowledge-linked cases cannot bypass review; explicit legacy manual approval has
a labelled reviewer-authored basis. Keep `automation_execution_ui` default off;
`manual_test_results` is a separate default-off gate. No browser/model call is
authorized by recording a manual result.

Account AI allowance/pricing amendment (2026-11-12): see
`docs/mvp/AI_ALLOWANCES_PRICING.md`. Versioned accounts retain separate Managed
credits and BYOK requests even when the rollout flag is disabled. Never reset
usage on mode changes or migrate at startup. Prices are experimental; no checkout
or paid mode entitlements are delivered. Credits are not tokens or cost guarantees.

Updated 2026-10-31. Current target: a human-supervised, recording-trained visual QA SaaS. This is an incremental evolution of AI QA Team, not a rewrite.

## Sources of truth and evidence

- `docs/mvp/PERFORMANCE_ASSESSMENT.md`: navigation investigation, current local fixes,
  measured production first/warm request limits and remaining qualification work.

- `docs/mvp/MVP_SPEC.md`: target scope and acceptance criteria.
- `docs/mvp/REPO_GAP_ANALYSIS.md`: implementation assessment, evidence and verification limits.
- `docs/mvp/IMPLEMENTATION_PLAN.md`: milestones, migration and effort estimates.
- `docs/mvp/DECISIONS.md`: accepted constraints, hypotheses and open decisions.
- `docs/mvp/PRODUCT_KNOWLEDGE.md`: development knowledge review, story analysis and scenario/testcase distinction.
- `docs/mvp/APPROVED_EXECUTION_DELIVERY.md`: seven-task execution status and merge gates.
- `docs/mvp/HYBRID_EXECUTION_PLAN.md`: proposed semantic-first targeting amendment, phases and qualification gates; planning only.
- `AI_QA_TEAM_SKILL.md`: architecture and safety guidance aligned to this target.
- `CODEX_CONTEXT_PROMPT.md`: task workflow and handoff guidance.

Read the relevant documents before architectural changes. Current user instructions govern task scope. The MVP documents govern product scope; actual code and reproducible checks establish implemented behavior. Resolve material conflicts explicitly rather than silently changing architecture. The 2026-10-31 audit referenced `dev` at `2479de4017cd8e29516daa1ecf62d5763bc2b6b2`; recheck the current checkout. This documentation alignment did not inspect or execute the repository.

The three root guides now supersede their older brownfield-only sequencing. The statement in the earlier DECISIONS document that these guides remain unchanged is historical. Recording-led priority is already accepted; do not ask the user to reconfirm it. Repository import, matching and data-engine work are not prerequisites.

## Product and execution boundary

Primary journey: Train product knowledge → review/clarify and approve knowledge → add story + acceptance criteria → generate/review/approve tests → execute → review evidence → approve corrections when needed.

Recordings supply product knowledge; stories and acceptance criteria define test intent and expectations. Retain and adapt story-based Test Generation as the primary specification workflow. Flag conflicts with approved knowledge before generation; unresolved material conflicts block generation until reviewed. Every test version links to its story, specific acceptance criteria and approved knowledge version. Explicit approved expected results are required before execution. Corrections create reviewed successor versions, flag affected tests and preserve prior approvals and historical run references. Teach-back is optional within knowledge review; any browser demonstration still requires approved bounded actions and expectations.

Reusable workflows are optional. Users can author inline case steps or link exact
approved reusable versions, including login only when needed. Credential inputs
reference the selected environment role. See `docs/mvp/APPROVED_WORKFLOWS.md` for
the default-off development authoring/approval/preview slice and its runtime limits.
It does not implement general browser execution. Preserve the synthetic adapter.

Account/project onboarding is reusable but is not product training. Training means ingestion and review of knowledge, not model fine-tuning. Users interact through a web app; the SaaS pilot needs no local customer agent. Local execution is initially a developer proof.

New executor: Robot Framework core → custom Python visual library → direct HTTPX WebDriver client → ChromeDriver → matched Chrome for Testing. No Selenium, Playwright or Puppeteer clients, including transitive dependencies, in that isolated runtime. Preserve legacy Playwright separately. Static source scanners for those frameworks are not runtime clients.

Screenshots/computer vision identify UI targets; approved natural-language tests compile into bounded structured specifications. Trusted code performs coordinate/key actions and validates checkpoints. Do not silently add DOM/selector targeting, arbitrary JavaScript, generated code or unrestricted Robot keywords. WebDriver is a protocol, not a Selenium client requirement. Robot core alone supplies neither browser control nor vision.

The user has requested a semantic-first hybrid **plan**, recorded in
`docs/mvp/HYBRID_EXECUTION_PLAN.md`. It proposes an explicit amendment to the above
targeting constraint, not a hidden fallback or delivered feature. When implementation
is assigned, start with H0/H1: version the policy/contracts and update guidance,
then prove the supported direct-WebDriver semantic subset. Do not treat this
planning task as authority to change application behavior or approved versions.

## Mandatory invariants

Current development additions (2026-11-11): default-off `product_knowledge` and
`story_analysis` support document/timestamped-transcript sources, reviewed immutable
knowledge snapshots, blocker review and knowledge-linked scenario intents/detailed
testcase drafts. This is not recording upload/transcription. Compiled specifications
pin knowledge/analysis and can save non-executable immutable run admissions.
General worker, credential-safe visual execution and real integration remain
unfinished; never interpret a prepared admission as a queued/started run. BrowserStack
is the accepted first development provider for the assigned execution work,
superseding its earlier deferred listing; preserve a reusable adapter boundary.
The default-off `approved_workflow_worker` now supports a separately queued
`about:blank` readiness operation via an isolated Robot/HTTPX process, not general
case execution. Read `docs/mvp/WORKFLOW_WORKER.md` for leases, private event safety,
cleanup/reconciliation and measured real-Mongo/BrowserStack limits. A ready browser
cannot pass the approved test; unknown cleanup holds capacity. API startup must
not launch this worker or attach its jobs to legacy consumers.

- MongoDB is durable truth; Redis is coordination/cache. Reuse existing services and feature configuration where appropriate.
- Authorize every project reference, query, artifact and job. Platform roles do not bypass project membership. Application roles are distinct from project roles.
- Expected, observed, inferred and unknown information remain distinct. Observations never automatically become approved requirements.
- Approved knowledge/tests are immutable versions; edits create successors and flag affected cases. Runs pin exact approved versions, configuration and evidence identity.
- Repository-derived work additionally pins exact source commit/registry identity. Recording-only runs do not require a repository or invented commit.
- Every required assertion must be evaluated reliably before Passed. Missing assertions, navigation success and stub completion cannot pass.
- Lifecycle and verdict are separate. Verdicts: Passed, Failed, Blocked, Needs review, Cancelled. Preserve legacy raw results.
- Models propose; trusted code enforces access, action allowlists, network rules, budgets, retries and deterministic comparisons. Treat page and training content as untrusted data.
- Never expose secrets in Redis, logs, API responses, history or model inputs. Resolve scoped secret references inside trusted runtime; redact images and media as well as text.
- Never blind-retry a consequential action or an entire browser run after an uncertain submit. Reconcile or request review.
- Preserve old routes, data and working behavior. New visual mode requires explicit adapter/job identity and independent gates, not automatic fallback or enabling legacy native execution.
- Keep customer repositories read-only by default and artifacts in isolated workspaces. Do not delete features/dependencies as incidental cleanup.

## Scope and delivery order

Pilot: one module, 3–5 workflows, two application roles maximum, 10–20 reviewed cases, English recordings up to 30 minutes, one validated Chrome/Linux configuration, batches of up to 10 approved cases, with checks within and across batches eligible for concurrent execution in a shared configurable pool (initial development default: five active checks). One isolated container/browser per active check; excess checks queue. Within-batch parallel execution is accepted MVP scope (2026-11-02), superseding the earlier two sequential-batch-container design; the default-off synthetic backend and Lab UI implement its mechanical subset, not approved customer/business tests. See docs/mvp/EXECUTION_CONTRACTS.md and M1A evidence. One active browser session per check container; fresh sessions for independent cases, per-case evidence/outcomes and per-case/batch budgets. Batch cancellation stops all its active check containers and cancels queued checks; never replay an interrupted batch or uncertain action. Enforce atomic global/account/project/environment slots, independent cancellation/evidence, budgets and shared-data conflict serialization; drain existing sequential batch/singleton work before the check pool launches; preserve legacy histories. Scheduled execution and high concurrency remain deferred. Cloud defaults to headless; visible local debugging is supported in separately launched sessions.

1. Isolated Windows visual proof against a synthetic controlled app; no real credentials or production services.
2. Immediately after proof, an explicitly scoped WSL/Linux and GCP feasibility spike; do not postpone cloud risk discovery until final qualification.
3. Platform access/secrets remediation and versioned contracts before customer-app execution.
4. Recording ingestion, reviewed knowledge (optional teach-back), and story/acceptance-criteria-based test design.
5. Durable orchestration, budgets, evidence, cancellation and pilot qualification.
6. Controlled evaluation and supported-provider BYOK beta after core gates.

These are priorities, not blanket authorization to implement or deploy every stage. A synthetic proof can proceed alongside independently scoped remediation. Real customer data/execution requires the security gate; paid pilot requires reliability and cost evidence; public self-service requires additional abuse/entitlement controls.

Managed AI first; extend AIUsageService → LLMGateway → ProviderRegistry → Provider. No multi-agent swarm, Obsidian, MAK4I or graph-database requirement. Live meetings, BrowserStack/Sauce Labs, private runners, general MFA/CAPTCHA, scheduling, arbitrary AI endpoints and broad browser support are deferred.

## Existing features and working discipline

Classify features as keep/reuse, adapt, preserve behind flags, defer, or investigate removal. Record evidence, callers/dependencies, data and migration impact. Out of scope does not mean safe to delete. Preserve static scanners, registry, bug interpretation, legacy history and optional flows without advancing their old roadmap.

Before changes inspect git status, relevant code and dependencies; preserve user edits. Make the smallest coherent change. Use existing Pydantic flags and guard API/job/model side effects as well as UI. Never inspect/print `.env` secrets or use production for routine tests. Startup creates Mongo indexes: use isolated services/fixtures.

Verification recorded by the prior audit, not rerun here:
- API entry: `python -m uvicorn app.main:app --reload` from `ai-qa-team-api`, with explicit development services.
- UI: `npm run dev` from `ai-qa-team-ui`; inspect `API_BACKEND_URL` and `NEXT_PUBLIC_API_URL` usage without exposing secrets.
- API Windows command: `..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_value_ownership.py -v` — eight passed in that audit.
- UI: `.\node_modules\.bin\tsc.cmd --noEmit --incremental false` — passed in that audit.
- `test_feature_flags.py` stalled and was interrupted; unresolved. Full suites, browser, cloud and real AI were not verified.
- Manifests/requirements/lock files diverge; establish a reproducible environment rather than casually regenerating dependencies.

Run checks appropriate to the change and `git diff --check`. Report changed files, behavior, compatibility/migration impact, actual checks, unresolved risks and next bounded task. Never present intended behavior or stale audit claims as current validation.

## M1A implementation status

`docs/mvp/M1A_DEVELOPMENT_SLICE.md` and `visual-runner/README.md` document the integrated Windows lab, actual checks and bounded M1B. `visual_runner_lab` is default off and development-only; it uses separate Mongo metadata and an isolated Robot/HTTPX environment, never the legacy queue. Fixture coordinates/keyboard actions are explicitly authorized for M1A only. Completion is a mechanical smoke check, not a business pass or visual AI validation. Preserve the controlled sample-only boundary. M1B must add real visual proposals, independent assertions and usage controls before claiming full M1.

Current stabilization evidence is in `docs/mvp/M1A_DEVELOPMENT_SLICE.md`: real UI login/API/TLS Mongo checks passed with explicitly configured cached CfT; the fresh-install 10-headless/5-headed series failed and remains a blocker. Regression tests are distinct from that real-service evidence. Do not describe M1A as clean-install verified until the fresh Windows startup cause is fixed and retested. The bounded Linux-only M1B experiment may proceed under the 2026-11-03 scope amendment below while Windows and Linux five-way reliability remain open. No cloud/customer readiness is established.


Linux spike status (2026-11-02): isolated Podman :guard image and explicit local
stopped-container reconciliation are verified for bounded synthetic cases; see
`visual-runner/linux/README.md` and M1A evidence for commands/denominators. Real
forced-stop reconciliation, actual 100s+10s outer-watchdog fault and completed-state
preservation each passed once. This is not automatic/multi-host reconciliation or
Linux API/UI/Mongo integration. Preserve the Windows qualification blocker; apply the current bounded Linux M1B scope below.


Batch backend (2026-11-02): `docs/mvp/EXECUTION_CONTRACTS.md` defines canonical
v1 models, schema export/check, default-off `visual_runner_batches`, pinned local
image settings and exact tests. This is synthetic/unbilled development only, separate
Mongo records and Podman containers, never legacy consumers. Old Windows start is
mutually gated while batch mode owns capacity. Do not claim real login/UI, customer
assertions, distributed safety or entitlements from ASGI fixtures with auth doubles.


Batch UI (2026-11-02): the existing Lab now calls synthetic batch APIs under both
flags; canonical models generate UI types through the contract exporter. UI tests
use intercepted auth/API and do not establish real-login integration. See current
EXECUTION_CONTRACTS.md/M1A commands and evidence. Customer URLs remain disabled.


Per-check pool revision (2026-11-02): parallel checks within a batch are accepted
MVP scope. One container per active check; configurable shared pool defaults to five,
not two sequential batch containers. Preserve/drain old batch history and ownership.
Implementation is present, but five-browser qualification is incomplete: first real
attempt 0/5 (browser-launch ReadTimeout), separate control ENGINE_UNAVAILABLE.
See EXECUTION_CONTRACTS.md/M1A for evidence and cleanup uncertainty. Do not claim
five-way readiness from configuration/unit tests. Bounded Linux M1B may proceed
under the current accepted scope; this does not qualify M1A or five-way reliability.


Preparation checkpoint (2026-11-03): durable sanitized preparation stages and first
error retention through reconciliation/parent UI are implemented. Historical
pre-start cause remains unknown. Real private Mongo/Podman fixtures: two one-case
controls completed; five preparations succeeded but workflows completed 4/5, with
one explicit ChromeDriver session rejection. Cancellation/PID0/slot release and
missing-image fault retention passed. Auth was a double; normal-login/UI was not
rerun. See M1A/EXECUTION_CONTRACTS. Five-way readiness remains unqualified; M1B is not implemented. Its bounded Linux
experiment is now accepted under the scope amendment below.


## Current Linux M1B scope amendment (2026-11-03)

Retain five concurrent Linux check slots as MVP target/configurable development
capacity, one isolated container per check. Do not reduce the target/default to
two. The user reports a successful parallel two-check UI batch; this is reported
evidence, not independent five-way qualification. Windows fresh-install reliability
and Linux five-way reliability (latest measured 4/5 workflows) remain open.

A bounded Linux-only M1B experiment may proceed alongside those issues; their
resolution is no longer a prerequisite for that experiment. See DECISIONS A14 and
IMPLEMENTATION_PLAN's current M1B task for acceptance and limits. Start with one
screenshot-identified visible button, trusted action and safe ambiguity stop;
then add bounded wait/scroll, independent positive/negative assertions, selective
evidence and latency/usage budgets. Preserve Robot/direct WebDriver, sample-only
network restrictions, project authorization, cancellation, five-slot scheduling and
no-replay behavior. Temporary observations are bounded and discarded; retain required
checkpoint/assertion/failure evidence. No DOM/JS targeting fallback or fixed-coordinate
claim of visual targeting. Customer execution, production/cloud deployment and
full MVP readiness remain gated. This amendment records scope only; it does not
implement M1B or authorize model calls in a documentation task.


Platform prompt governance: see `docs/mvp/PLATFORM_PROMPTS.md`. Only platform
OWNER/ADMIN manages shared task prompts, never project admins. Private backend
`PLATFORM_OWNER_EMAIL` bootstraps the trusted owner; changing it does not revoke
persisted roles. Project knowledge remains scoped, reviewed memory, not fine-tuning.


Current delivery priority (2026-11-12): complete Phase 1 Test Design before advancing
Execution MVP. See `docs/mvp/TEST_DESIGN_MVP.md` for incomplete release gates,
`PLATFORM_PROMPTS.md` for platform-only prompt phases, and `UI_UX_REFRESH.md` for the
shared workspace/dialog patterns and verification limits. Preserve existing runtime
features. Private recording storage/upload/transcription are not delivered.


Customer accounts (2026-11-12): see `docs/mvp/CUSTOMER_ACCOUNTS.md`. Default-off `customer_accounts` adds one customer account per user, naming in existing onboarding, account-admin invitations and same-account project membership. Preserve platform/project role separation. Existing-user ownership requires explicit reviewed migration; login must not create accounts. Flag-off does not remove isolation for assigned records. Billing/usage migration and per-account display numbering are not implemented.


Account Team/shared billing amendment (2026-11-12): see `docs/mvp/ACCOUNT_TEAM_BILLING.md`. Account OWNER/ADMIN manages same-account project assignments centrally; project-content/evidence access still requires membership. `account_subscriptions` is default off; billing cutover is an explicit reviewed migration, after which the account subscription is canonical even if the flag is disabled. Preserve legacy user subscriptions and histories; do not silently reset usage or apply existing-data migration at startup. Account-local display IDs remain future work.


Account UI refinement: see `docs/mvp/ACCOUNT_UI_REFINEMENTS.md`. Keep `test_execution_ui` and `account_invitation_email` default off. Manual invitation links remain active until SMTP is configured; never blind-retry ambiguous mail submission or expose email-mode invitation tokens. Free account member allowance is two additional identities, not per-project assignments.
