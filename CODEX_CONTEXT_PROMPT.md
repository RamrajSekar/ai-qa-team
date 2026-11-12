# AI QA Squad — Codex Repository Task Context

Updated 2026-10-31. Use this context with a concrete task; it is not an instruction to build the whole roadmap in one session.

## Objective and required reading

For the next targeting task, read `docs/mvp/HYBRID_EXECUTION_PLAN.md`. This is a
planning-only proposal for semantic-first hybrid resolution; H0/H1 are the first
implementation gates. Preserve the current runtime until an explicit implementation
task applies the contract/guidance amendment. Do not infer full accessibility-tree
support, deterministic VLM behavior or automatic conversion of old approved tests.

Also read `docs/mvp/PRODUCT_KNOWLEDGE.md` and `docs/mvp/APPROVED_EXECUTION_DELIVERY.md`
for the current development slice and incomplete execution/merge gates. Preserve
the document/transcript-only limitation, scenario-intent/testcase-procedure distinction
and non-executable prepared admissions. BrowserStack is the accepted first development
adapter for this assigned work; do not mistake that decision for customer readiness.
Read `docs/mvp/WORKFLOW_WORKER.md` before extending dispatch: current real browser
support is a separately supervised readiness operation, not the general interpreter.
Preserve session-event delivery outside Robot stdout capture and hold capacity until
remote cleanup is confirmed. Do not replay interrupted work or weaken its verdict.

Evolve the existing AI QA Team platform into a human-supervised, recording-trained visual QA SaaS. Read `AGENTS.md`, `AI_QA_TEAM_SKILL.md`, and `docs/mvp/{MVP_SPEC,REPO_GAP_ANALYSIS,IMPLEMENTATION_PLAN,DECISIONS}.md`. Current user instructions define the task. Scope documents define targets; inspected code and checks establish current implementation.

The old repository-first orchestration/synthetic-data roadmap is optional preserved work. Recording-led priority is already accepted. Do not request reconfirmation or require repository import before training/testing. The earlier statement that root guides remain unchanged is historical; these guides have now been consolidated.

Primary flow: Train product knowledge → review/clarify and approve knowledge → add story + acceptance criteria → generate/review/approve tests → execute → review evidence → approve corrections when needed.

Recordings supply product knowledge; stories and acceptance criteria define test intent and expectations. Retain and adapt story-based Test Generation as the primary specification workflow. Flag conflicts with approved knowledge before generation; unresolved material conflicts block generation until reviewed. Every test version links to its story, specific acceptance criteria and approved knowledge version. Explicit approved expected results are required before execution. Corrections create reviewed successor versions, flag affected tests and preserve prior approvals and historical run references. Teach-back is optional within knowledge review; any browser demonstration still requires approved bounded actions and expectations.

Account onboarding is not product knowledge training. Do not claim those new capabilities exist just because project setup is implemented.

## Non-negotiable implementation constraints

- Preserve Next.js/TypeScript, FastAPI/Pydantic, Mongo and useful Redis services. Avoid a stack rewrite.
- New isolated execution: Robot core → custom Python visual library → HTTPX direct WebDriver → ChromeDriver → matched Chrome for Testing.
- No Selenium/Playwright/Puppeteer client dependency, direct or transitive, in the new runtime. Preserve legacy Playwright separately; existing static scanners remain valid assets.
- UI target identification is screenshot/computer vision based, with natural-language specifications. No hidden DOM/selector fallback, arbitrary JavaScript, generated code or unrestricted Robot keywords.
- Backend coordinates specialized AI tasks; no swarm, new agent framework, Obsidian, MAK4I or graph database requirement.
- Models propose; trusted code authorizes bounded actions, permissions, network rules, secrets and budgets.
- Human approval applies to knowledge, optional teach-back demonstration actions and test versions. Runs pin immutable approved snapshots. Never infer correctness from observed UI alone or silently weaken assertions.
- All required assertions must be evaluated to pass. Verdicts are Passed, Failed, Blocked, Needs review, Cancelled; lifecycle is separate.
- Final SaaS uses cloud execution without customer installation. Local Windows proof precedes WSL/Linux and early GCP spike. Cloud defaults to headless; headed debugging uses a separately started session.

## Scope boundaries

Pilot: one module, 3–5 workflows, two roles maximum, 10–20 cases, English recordings up to 30 minutes, one supported Chrome/Linux configuration, batches of up to 10 approved cases, with checks within and across batches eligible for concurrent execution in a shared configurable pool (initial development default: five active checks). One isolated container/browser per active check; excess checks queue. Within-batch parallel execution is accepted MVP scope (2026-11-02), superseding the earlier two sequential-batch-container design; the default-off synthetic backend and Lab UI implement its mechanical subset, not approved customer/business tests. See docs/mvp/EXECUTION_CONTRACTS.md and M1A evidence. One active browser session per check container; fresh sessions for independent cases, per-case evidence/outcomes and per-case/batch budgets. Batch cancellation stops all its active check containers and cancels queued checks; never replay an interrupted batch or uncertain action. Enforce atomic global/account/project/environment slots, independent cancellation/evidence, budgets and shared-data conflict serialization; drain existing sequential batch/singleton work before the check pool launches; preserve legacy histories. Scheduled execution and high concurrency remain deferred. Managed AI first. Supported-provider/model BYOK and controlled evaluation follow core gates.

Defer live meetings, BrowserStack/Sauce Labs, customer/private runners, general MFA/CAPTCHA, advanced native/file/drag-drop interaction, mobile, broad browsers, schedules/high concurrency, arbitrary model endpoints, autonomous release decisions and full billing.

Do not advance matcher/planner/four-layer-data-engine work unless explicitly assigned. Keep old discovery, bug interpretation, recorder, Story/Scenario and execution assets. No broad feature deletion, dependency removal, schema rewrite or automatic fallback.

## Evidence-aware starting point

The previous audit used `dev` at `2479de4017cd8e29516daa1ecf62d5763bc2b6b2`. Recheck the actual branch/commit and relevant source. The attached documentation review did not rerun the repository.

Reuse candidates: auth/project membership, environments, feature flags, subscriptions/usage, prompt versioning, provider gateway, encrypted BYOK store, static scanners and registry. BugInterpreter/TestIntentV1 already exist as interpretation/review; matcher/planner and durable product learning do not. Provider requests were text-only despite vision catalog labels.

Prior audit findings requiring safe verification: testcase authorization, plaintext application credentials in environment/queue/response paths, sensitive logs, mutable approval booleans, pass stubs/incomplete assertions, destructive queue handling, possible double usage accounting, cloud runner stub and dependency drift. Do not label source findings reproduced, fixed or production-safe without evidence.

## Next milestone and release gates

Unless a different implementation task is supplied, recommend the isolated M1 visual proof; do not automatically execute the entire roadmap. In a documentation/review task, remain documentation-only.

M1 uses a controlled synthetic app and no real credentials. Prove approved specification → screenshot observation → bounded action → independent assertion through the prescribed execution stack. Include form input, basic dropdown, scrolling, calculated total and confirmation; test a deliberately wrong result, ambiguous target, timeout after submit, cancellation and cleanup. A screenshot/driver smoke test alone is insufficient.

Immediately afterward schedule an explicitly scoped Linux/GCP feasibility spike, not only final M6 qualification. Distinguish these gates:
- Synthetic proof: bounded executor evidence and isolated dependency graph.
- Customer-app access: tenant isolation, secret references, safe logs, network restrictions and version approval.
- Paid pilot: complete workflow, durable runs/evidence, measured reliability/cost and retention.
- Public self-service: additional abuse controls, entitlements and safe evaluation scope.

Do not block a safe synthetic proof on every production subsystem, but do not use proof success to bypass the customer-data gate. If the approved execution approach fails, report it and propose a scoped decision; never silently substitute Playwright/Selenium.

## Required engineering checks

- Inspect git status and relevant code before editing; preserve existing user changes.
- Identify reusable boundaries and implement the smallest coherent change.
- Scope every API/query/object/job reference to project membership; platform roles do not bypass it.
- Resolve secrets trusted-side. Never print `.env`, credentials, cookies, raw sensitive prompts or secret-bearing screenshots.
- Reuse AIUsageService → LLMGateway → ProviderRegistry → Provider; extend bounded operation policies and multimodal capability tests.
- Count retries, tokens/images/transcription/browser usage; enforce configurable budgets. Existing credits are not a proven dollar cap.
- Keep model proposals schema-bound; validate fresh screenshot identity, coordinates, scale, action permissions and postconditions.
- Pin exact knowledge/test/configuration versions; additionally pin source commit only for repository-derived work.
- Separate visual dispatch/queues from legacy worker consumption. No blind retries after uncertain consequential actions; reconcile duplicate/crashed/cancelled work.
- Keep artifacts private, durable and retention-aware, with explicit incomplete evidence reporting.
- Preserve histories and additive compatibility; do not convert legacy booleans into approved versions or legacy passes into evidence-backed passes.
- Verify API/worker/UI feature gates separately; no second flag service. Do not enable old native execution as a shortcut.
- Run meaningful focused tests. Use isolated fixtures/services because startup initializes Mongo indexes. Never use production for routine checks.
- Diagnose rather than conceal the previously stalled `test_feature_flags.py`. Prior audit's eight ownership tests and TypeScript check are historical, not current test results.
- Do not casually regenerate divergent dependency manifests. Verify the new runner's full installed dependency graph and licenses separately.

## Feature-disposition audit

For existing features outside the new journey, record:

| Feature/path | Current evidence | Disposition | Dependencies/data/callers | Proposed change | Risk and effort |
| --- | --- | --- | --- | --- | --- |
| Populate from inspected repository | Implemented / partial / stub / unknown | Keep/reuse / adapt / preserve behind flags / defer / investigate removal | Include API, worker and storage impact | Separate recommendation from implementation | Range and assumptions |

Out of scope is not synonymous with unused. Do not remove anything based only on a hidden menu or static search. Removal needs a scoped migration/caller assessment, retained history/export path and rollback. Preserve customer automation input ownership and exact values if legacy integration is touched.

## Deliverables for an assigned task

Report:
1. Actual branch/commit and inspected scope.
2. What was reused and what changed, with paths.
3. Behavior before/after and acceptance evidence.
4. Compatibility, permissions, data migration, dependencies and operational impact.
5. Tests/checks run, outcomes and explicit unverified areas.
6. Feature dispositions and deferred work relevant to this task.
7. Remaining effort in engineer-days/weeks with assumptions and uncertainty; no invented reuse percentages or precise line-count forecasts.
8. The next bounded task and any genuine unresolved decision.

Update affected MVP docs and these guides when an authorized implementation changes the facts. Do not preserve contradictory claims by appending another historical paragraph. Keep detailed scope/estimates in `docs/mvp/`; keep this prompt focused on execution discipline. Documentation changes do not authorize commit/push/deploy or unassigned application changes.


Per-check pool revision (2026-11-02): parallel checks within a batch are accepted
MVP scope. One container per active check; configurable shared pool defaults to five,
not two sequential batch containers. Preserve/drain old batch history and ownership.
Implementation is present, but five-browser qualification is incomplete: first real
attempt 0/5 (browser-launch ReadTimeout), separate control ENGINE_UNAVAILABLE.
See EXECUTION_CONTRACTS.md/M1A for evidence and cleanup uncertainty. Do not claim
five-way readiness from configuration/unit tests. Bounded Linux M1B may proceed
under the current accepted scope; this does not qualify M1A or five-way reliability.


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


For account work, read `docs/mvp/CUSTOMER_ACCOUNTS.md`: current default-off ownership/isolation slice, migration gates and verification limits. Preserve existing billing and IDs until explicitly scoped. Account assignment requires reviewed migration for existing users; account naming is in onboarding, never new-account creation during login.


Account Team/shared billing amendment (2026-11-12): see `docs/mvp/ACCOUNT_TEAM_BILLING.md`. Account OWNER/ADMIN manages same-account project assignments centrally; project-content/evidence access still requires membership. `account_subscriptions` is default off; billing cutover is an explicit reviewed migration, after which the account subscription is canonical even if the flag is disabled. Preserve legacy user subscriptions and histories; do not silently reset usage or apply existing-data migration at startup. Account-local display IDs remain future work.
