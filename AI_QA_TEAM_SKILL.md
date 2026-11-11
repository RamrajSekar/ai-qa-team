---
name: ai-qa-team-architecture
description: Repository-specific guidance for a human-supervised, recording-trained visual QA SaaS, preserving existing QA platform assets.
---

# AI QA Squad Architecture Guide

Updated 2026-10-31. This repository guidance replaces the former brownfield-only orchestration/data-engine roadmap. It does not install a separate agent system or authorize implementation. Read `AGENTS.md` and the four `docs/mvp/` documents first.

## Mission and scope

Train an AI QA practitioner through uploaded narrated product demonstrations; validate its understanding; approve tests; execute them through computer vision and natural-language specifications; retain reviewed corrections. One or two days describes supervised onboarding effort, not guaranteed autonomy or model training.

Customer path after project/access setup: Train product knowledge → review/clarify and approve knowledge → add story + acceptance criteria → generate/review/approve tests → execute → review evidence → approve corrections when needed. Account onboarding alone does not implement this path. Repository imports are optional.

Recordings supply product knowledge; stories and acceptance criteria define test intent and expectations. Retain and adapt story-based Test Generation as the primary specification workflow. Flag conflicts with approved knowledge before generation; unresolved material conflicts block generation until reviewed. Every test version links to its story, specific acceptance criteria and approved knowledge version. Explicit approved expected results are required before execution. Corrections create reviewed successor versions, flag affected tests and preserve prior approvals and historical run references. Teach-back is optional within knowledge review; any browser demonstration still requires approved bounded actions and expectations.

Pilot envelope: one module, 3–5 workflows, at most two application roles, approximately 10–20 cases, English, recording up to 30 minutes, one Chrome/Linux configuration, batches of up to 10 approved cases, with checks within and across batches eligible for concurrent execution in a shared configurable pool (initial development default: five active checks). One isolated container/browser per active check; excess checks queue. Within-batch parallel execution is accepted MVP scope (2026-11-02), superseding the earlier two sequential-batch-container design; the default-off synthetic backend and Lab UI implement its mechanical subset, not approved customer/business tests. See docs/mvp/EXECUTION_CONTRACTS.md and M1A evidence. One active browser session per check container; fresh sessions for independent cases, per-case evidence/outcomes and per-case/batch budgets. Batch cancellation stops all its active check containers and cancels queued checks; never replay an interrupted batch or uncertain action. Enforce atomic global/account/project/environment slots, independent cancellation/evidence, budgets and shared-data conflict serialization; drain existing sequential batch/singleton work before the check pool launches; preserve legacy histories. Scheduled execution and high concurrency remain deferred. Validate forms, links, buttons, basic dropdowns, tables and scrolling on the actual pilot app. General MFA/CAPTCHA, native dialogs, advanced drag/drop, mobile and desktop are deferred.

## Reuse and implementation evidence

The prior source audit at `2479de4017cd8e29516daa1ecf62d5763bc2b6b2` reported the following; verify relevant code before changing it. This revision is a document review, not a new repository audit.

| Area | Reported state | MVP treatment |
| --- | --- | --- |
| Next.js/React/TypeScript, FastAPI/Pydantic, Mongo, Redis | Existing foundation | Extend; avoid stack rewrite |
| Auth, projects, membership, environments, usage/subscriptions | Existing, with access/credential findings | Reuse and remediate before customer execution |
| Pydantic feature flags and `/features` | Existing | Extend one configuration system; true flags do not imply readiness |
| Robot, Playwright JS/TS, Selenium Java static scanners | Implemented structural discovery | Preserve; no runtime-client dependency implication |
| `discovered_tests`, TestContract provenance/ownership | Existing canonical registry | Preserve commit binding; semantic coverage fields remain empty |
| BugInterpreter / TestIntentV1 | Structured interpretation and review; no durable intent/matcher/planner | Optional preserved feature, not primary onboarding |
| Prompt Registry | Immutable version/activation pattern | Reuse pattern for governance; do not equate prompts with knowledge |
| AI gateway, provider registry, project BYOK, usage service | Text/JSON foundation and secret abstraction | Extend validated multimodal capabilities and cost controls |
| Recording learning, knowledge approval, visual executor | Targets | New work; not proven by flags/catalog metadata |
| Legacy Story/Scenario/Recorder/Playwright execution | Preserved default-off assets, with gaps | Explicit separate mode; no automatic fallback |

Do not repeat older claims that static scanners or BugInterpreter still need to be built. Conversely, source presence does not establish runtime reliability. The prior audit reported a manual pass stub, incomplete assertion checks, plaintext environment-secret paths, insufficient testcase scoping, sensitive logging, destructive LIFO queue consumption and possible usage double counting. Reproduce safely and remediate; do not claim verified exploitation or completed fixes.

## Architecture boundaries

Reuse the web app and API as the control plane. Isolate media processing and browser execution from API requests and one another. Use bounded task orchestration, not autonomous agent-to-agent delegation.

Mongo stores source metadata, approved knowledge/specification versions, permissions, run manifests, journals and usage. Private object storage holds media and evidence. Redis may retain current rate limiting/coordination; it is not the durable job registry. Embeddings are optional derived retrieval indexes scoped to project and version; a graph database is unnecessary for MVP. No Obsidian or MAK4I dependency.

Recommended cloud components are GCP services/Jobs, private GCS, Secret Manager and Artifact Registry, subject to the early spike. OCI images can be built with Podman; Docker Desktop is not a customer requirement. Final SaaS requires no customer install. Private-network runners and BrowserStack/Sauce Labs are later adapters.

## Knowledge and test contracts

Use framework-neutral, schema-versioned representations; final collection layout follows existing code and bounded document sizes.

- TrainingSource: project, private object reference, media identity, processing status, consent/retention, timestamped transcript and frame references.
- KnowledgeVersion: terminology, roles, pages/components, workflows, business rules, exceptions, unknowns; source evidence, confidence, reviewer changes and approval metadata.
- Clarification: unresolved claim/question, source references, answer, reviewer and resulting version.
- TestSpecVersion: purpose, role, preconditions, inputs, natural-language steps, bounded structured actions, explicit expected results/assertions, cleanup, story version, specific acceptance-criterion references, approved knowledge version and approval metadata.
- RunManifest: exact approved test/knowledge versions, project/environment/application-role references, model/prompt versions, adapter/image/browser/driver versions, viewport, limits, artifact identity and initiating user.
- ActionJournal/AssertionResult: intent, fresh observation identity, action/checkpoint, expected/observed comparison, uncertainty and evidence.

Separate expected, observed, inferred and unknown. Recorded UI behavior is evidence, not automatically the correct requirement. Every assertion needs approved knowledge or an explicit reviewer-authored expectation. Confidence is evidence metadata, not authorization or a calibrated probability by default.

Approval publishes an immutable version atomically. Edits produce draft successors; changed rules flag dependent tests. Runs use exact version snapshots; stale approvals cannot authorize edited content. Retention/deletion obligations still apply to immutable records and derived artifacts.

Optional teach-back within knowledge review includes explanation and, when requested, a bounded browser demonstration with reviewed actions and expectations. It does not grant open-ended exploration or establish coverage by itself.

## Visual execution contract

Robot core → custom Python visual library → HTTPX direct WebDriver → ChromeDriver → matched Chrome for Testing.

The complete isolated dependency graph must exclude Selenium/Playwright/Puppeteer clients, SeleniumLibrary and Robot Browser library. Preserve legacy dependencies in their own environment. WebDriver is a standard protocol; ChromeDriver is still required. A direct client means owning session, timeout, error, screenshot and input-protocol handling.

Use RunnerAdapter prepare/execute/collect/cleanup boundaries and normalized results. Distinguish the new visual adapter from future execution of imported Robot suites. Do not require a customer repository, source commit, locator or executable test code for story-authored visual tests informed by recording-derived knowledge.

Vision/NLP proposes a target/action from redacted screenshot evidence. Trusted code validates schema, allowed action, screen identity/freshness, bounds, scale, origin, permission and remaining budgets before coordinate/key dispatch. Reobserve after scroll/navigation/viewport change. Do not use hidden DOM/selector fallback or arbitrary browser scripts to conceal vision failures.

Use fixed supported actions such as navigate, click, type, scroll, wait and observe; validate dropdown interaction on the supported widget set. No model-generated Python, shell, JavaScript, general Robot programs or unrestricted keywords. Exact comparisons are deterministic over reliable extracted observations; uncertain OCR/model reads must remain uncertain. Observe postconditions independently of action completion.

Lifecycle is distinct from verdict:
- Passed: every required assertion reliably evaluated and satisfied.
- Failed: reliable contradiction of an approved expectation.
- Blocked: missing prerequisite or execution problem prevents completion.
- Needs review: ambiguous evidence or interpretation.
- Cancelled: deliberately stopped.

Empty assertions and missing evidence cannot pass. Preserve original legacy outcomes and separate bug-reproduction semantics. Bounded target reacquisition cannot change expected behavior, bypass a tested defect, or retroactively convert a failed run into a pass. Persistent repairs require a reviewed successor version.

## Reliability, security and browser operations

Persist approved manifest before dispatch; use explicit mode/version payloads and separate dispatch identities so legacy workers cannot consume visual jobs. Use durable outbox/lease/fencing and action checkpoints as justified by the release gate. Deduplicate initiation; recognize that delivery deduplication cannot guarantee exactly-once external UI effects. Initially disable automatic whole-job retries. Uncertain submission requires reconciliation/review, never blind resubmission.

Support cancellation and stale-run reconciliation. Close browser/driver and per-run profile on every normal exit; reconcile after process death. Persist private evidence and explicit incomplete-artifact status when uploads fail; never publish a misleading complete report.

Project authorization covers every query, cross-reference, vector retrieval, object URL and job. Platform OWNER/ADMIN does not grant customer-project access. Project ADMIN/TESTER is independent of application roles. Preserve lazy creator-membership backfill; do not guess ownership.

Application and provider secrets use references and trusted runtime resolution. Existing AES-GCM encrypted Mongo SecretStore is a reusable abstraction, not proof all environment credentials are safe. Keep its master key outside Mongo, stable and securely managed; migrate/rotate deliberately. No raw secrets in queues, prompts, logs, history, responses or screenshots. Review/drain/quarantine old secret-bearing jobs deliberately; never blindly execute or delete them.

Treat recordings, transcripts, frames, pages and imported code as untrusted input. Restrict media decoding resources. Enforce browser egress beyond top-level URL validation: redirects, DNS changes, subresources and metadata/private addresses require network controls and explicit staging exceptions. Driver is private loopback, not publicly exposed. Use isolated profiles and no shared cookies.

Pin matched Chrome for Testing/ChromeDriver bundles in versioned images; do not mutate active runners. Automate release discovery, compatibility tests and canaries, including security patches, then promote/rollback images. Record versions per run. Validate sandbox behavior, fonts, viewport, memory, cleanup and headless parity on Linux and actual GCP. Do not silently disable the sandbox to pass a smoke test. Dependency/license notices must cover the resolved image including media/OCR/browser binaries.

## AI stages and usage controls

New production calls go through feature → AIUsageService → LLMGateway → ProviderRegistry → Provider. Reuse Prompt Registry versioning. Existing catalog vision labels are not proof of working image requests; add provider capability tests.

| Stage | AI use | Restriction |
| --- | --- | --- |
| Training ingestion | Speech transcription | Duration/file limits; one durable result per source identity |
| Knowledge extraction | Selected frames + transcript; rules/questions | Bounded chunks/output; source links; drafts only |
| Optional teach-back within knowledge review | Explain approved knowledge | Version-scoped retrieval; no new requirements |
| Test design | Propose cases from stories/acceptance criteria using approved knowledge context | Pre-generation conflict review; source/version links; explicit expected results; case limits and human approval |
| Execution | Visual target/action proposal; uncertain observation interpretation | Fresh images; bounded schema/actions/calls; deterministic authorization |
| Diagnosis | Explain collected failure evidence | Evidence-only summary; cannot rewrite verdict |
| Maintenance | Propose knowledge/test corrections | New draft + impact review; no silent healing |

Deterministic code handles authorization, media validation, scheduling, arithmetic/comparisons, persistence, entitlements and policy. Avoid sending full recordings, whole memory or repeated unchanged screenshots on every call. Retrieve only relevant approved facts, sample/crop frames without losing necessary context, cache by project/content/version/model identity, and invalidate on corrections. Never reuse stale visual targets after UI changes.

Starting hypotheses: 10 minutes/run, 40 input actions, 30 model calls, two ambiguity reobservations per target, plus run/daily/account spend ceilings. Count retries and failed calls. Reserve allowances atomically, reconcile actual usage, and distinguish model tokens, transcription minutes, image usage, browser time and customer credits. Existing credit guards do not yet establish dollar budgets; unknown provider cost is not zero. Set versioned prices/estimates and enforce ceilings conservatively.

Managed first; supported-provider/model BYOK beta later. Existing project-admin OpenAI/Azure settings are reusable; organization ownership remains a decision. Validate vision/structured-output/transcription capability per task, allowlist endpoints, encrypt keys, audit rotation/revocation and prohibit silent provider/account fallback. BYOK still consumes platform resources and allowances. Arbitrary endpoints/self-hosted models are deferred.

## Preserved legacy rules — optional track only

Keep customer repositories read-only, generated artifacts outside their working tree and discovery/execution bound to the same exact commit. `discovered_tests` remains the existing registry; do not duplicate it. Static provenance/ownership is not semantic coverage.

Preserve BUG_LOCKED/EXACT values and BUG_CONSTRAINED constraints. Inject only required external/user-intent values; do not override internally generated data or seed runtime outputs. UNKNOWN required dependencies block or require review. Separate generation of synthetic values from resolution of real valid inventory.

If legacy matching/reproduction is explicitly scoped, distinguish FULL/PARTIAL/NONE coverage; partial setup is useful but not full reproduction. Never silently fill imported automation gaps with visual execution. Bug verdicts REPRODUCED/NOT_REPRODUCED/INCONCLUSIVE/BLOCKED are separate from runner results. Preserve framework-managed dataset iteration when applicable.

Four-layer data generation, matcher/planner, Jira connectors and expanded repository execution are deferred. Preserve source and data; do not follow the old scanner-to-data-engine implementation sequence.

## Delivery gates and measurement

1. Synthetic local proof: approved minimal JSON, controlled app, screenshot targeting, bounded actions, independent text/numeric assertions; wrong expected value, ambiguous target, submit timeout, cancellation and cleanup. Prove no prohibited transitive clients.
2. Early Linux/GCP feasibility spike immediately after local proof: actual headless job, image/sandbox, network path, resources, cleanup and evidence. This is distinct from later pilot qualification and requires its own scoped deployment task.
3. Customer-app gate: tenant isolation, reference-only credentials, no sensitive logging, approval/version correctness, network restrictions and cancellation before real recordings/credentials.
4. Paid pilot gate: full training-to-evidence workflow, durable execution, representative corpus, costs/support effort and retention validated.
5. Public evaluation gate: controlled demo first; abuse, quotas and deletion tested before broader access. Own-app invite only.

Provisional measurement hypotheses, not claims: ≥70% proposed cases accepted without substantive edits; ≥90% supported-flow completion; ≥90% seeded defect detection; zero observed critical false passes with denominator reported; ≥30% net human-time reduction including onboarding/review/maintenance. Define corpus, repeats, confidence/uncertainty, false-fail and needs-review rates before evaluating. Set a measured spend ceiling before pilot promises.

Core prior estimate: 32–52 engineer-weeks, 35 focused hours/week; free demo and BYOK another 5–9. These are low-to-medium-confidence planning ranges, not new estimates or a delivery commitment. Reestimate after proof/cloud spikes. Do not equate local demo success with paid-pilot readiness.

Evaluation hypothesis: one user/project, ten-minute recording, five cases/five bounded executions, seven-day screenshot retention, no scheduling; one-time trial allowance, not unlimited monthly usage. Platform-failed runs refund evaluation entitlement even if provider costs occurred. Pricing remains experimental; do not implement full billing as a proof prerequisite.

## Change discipline

Inspect source and git status; preserve user edits and existing IDs/history. Classify features before removal. Hiding navigation does not disable APIs/workers; guard side effects and queues independently. Use additive schemas and tolerant legacy reads; never retroapprove old boolean approvals or invent evidence.

Use timezone-aware timestamps and safe mutable defaults. Run focused meaningful checks and report limitations. The previous feature-flag suite stalled; do not label it passed. Avoid unrelated lockfile churn. Implement only the currently assigned milestone; documentation does not authorize migrations, production access or blanket deployment.


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
