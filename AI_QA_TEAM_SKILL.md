---
name: ai-qa-team-architecture
description: Repository-specific guidance for evolving AI QA Team into a repository-aware test orchestration and synthetic test data control plane.
---

# AI QA Team Architecture Skill

Use this skill whenever changing AI QA Team backend architecture, repository discovery, test data generation, environments, execution, runners, registry, or feature flags.

## Mission

Evolve the existing product incrementally into a Dynamic Agentic Test Orchestrator & Test Data Engine.

AI QA Team is a non-invasive QA control plane over an enterprise's existing automation: **use the automation the customer already owns; do not rewrite or replace it unnecessarily.**

Two entry modes share one platform:
1. Bug reproduction / test-state preparation: "Help me reproduce/prepare this bug using automation I already own."
2. QA exploration / strategic test data: "Help me explore this scenario using strategic datasets and automation I already own."

Robot Framework is the initial framework. Playwright and Selenium repository adapters are future work, not currently implemented orchestration.

```text
Existing Repository → Repository Scanner → Persistent Test Registry
→ TestContract + Capabilities → Intent / Reproduction Planning
→ Data Resolution / Data Engine → Execution Orchestrator
→ Existing Automation → Results / Evidence
```

This is the target architecture, not a claim of current implementation. Start with pasted bug description, Steps to Reproduce, Expected Result, and Actual Result. Jira URL/API/webhook integration is a later input adapter, never a prerequisite for MVP validation.


Do not replace customer tests with generated tests unless explicitly working on the legacy/greenfield workflow.

## Core invariants

### Preserve existing code
Story, Scenario, Recorder, Test Generator, Playwright execution, authentication, subscription, Mongo, and Redis code are assets.

Disable out-of-scope features with feature flags. Do not delete them just to simplify the MVP.

### Brownfield is the active MVP path

Phase 1 delivers discovery, registry/contracts, intent/reproduction planning, data resolution, preview/export. Phase 2 adds reviewed execution of existing automation and state capture. Both are planned; feature flags and existing infrastructure are current foundation.

### Robot first
Phase 1 and initial Phase 2 target Robot Framework only.

Architect for adapters, but do not prematurely implement Playwright/Selenium repository discovery.

### Repository is read-only by default
Do not modify customer-owned test files or committed data files.

Generated artifacts belong in an isolated execution workspace.

### Registry must be persistent
MongoDB is source of truth.

Redis is cache/queue only.

Every registry version must be tied to repository identity and source commit SHA.

### AI is targeted, not pervasive
Use AI for:
- intent matching;
- slot filling;
- strategic test-data reasoning;
- optional complex failure explanation.

Prefer deterministic code for:
- repository scanning;
- schema extraction;
- validation;
- cross-field rules;
- file creation;
- runner invocation;
- result parsing;
- deterministic failure classification.

### Keep secrets out of control-plane payloads
Never put plaintext passwords/tokens in Redis, logs, API responses, execution history, or LLM prompts.

Use credential/secret references.

### Environment != runner
Keep these distinct:

```text
environment: QA/UAT/STAGING/PROD
runner: robot-local/playwright-local/cloud
browser: chromium/firefox/webkit
```

### Canonical contracts first
Use framework-neutral contracts:
- TestIntent
- ReproductionPlan
- TestContract
- InputContract
- RuntimeDependency
- StrategyPlan
- GeneratedDataset
- ExecutionContext
- ExecutionResult
- BugReproductionResult

### Framework-specific work belongs behind adapters
For Phase 2 use RunnerAdapter + RobotRunnerAdapter.

## Existing feature flags — implemented

The source of truth is `ai-qa-team-api/app/config.py`: Pydantic `Settings.features` / `FeatureFlags`, with nested environment settings. The shared dependency/helper is `app/utils/feature_flags.py`; `GET /features` returns a read-only boolean map. Do not introduce a second configuration service or reimplement flags.

Actual code defaults:

```python
FEATURES = {
    "story_management": False,
    "scenario_generation": False,
    "test_generation": False,
    "recorder": False,
    "native_execution": False,
    "jira_trigger": False,
    "failure_diagnostics": False,
    "self_healing": False,
    "playwright_repo_adapter": False,
    "selenium_repo_adapter": False,
    "repository_discovery": True,
    "test_registry": True,
    "test_data_generation": True,
}
```

True policy switches do not prove these product areas are implemented or production-ready. The scanner, persistent Test Registry, new contracts, planners, data engine, and adapters below are planned work. Do not enable disabled features casually or delete their source.

Current guards block disabled requests before generation/usage/write/enqueue side effects. Disabled UI paths/actions are gated. With native execution disabled, new executions/enqueueing are blocked and the worker exits before consuming jobs; execution history reads remain available. Redis, Mongo execution persistence, worker, Playwright runner, and StepEngine code are preserved. The legacy Playwright import requires adapter, Story, Scenario, and Test Generation flags, so it cannot bypass those gates.

## TestContract and capability discovery (conceptual)

A framework-neutral TestContract contains identity (test_id, test_name, suite, tags), project/framework context, repository metadata (repository_id, file_path, source_commit_sha, registry_version, parser_version), Inputs, Runtime Dependencies, Capabilities/Steps, Assertions/Expected Behaviors, and Discovery Confidence.

Use the Robot scanner (`robot.parsing`) to discover more than variable names. Record evidence and uncertainty for inferred capabilities; do not equate keyword names with proven behavior. InputContract carries type/requiredness, ownership, provenance, constraints, generation eligibility and confidence; RuntimeDependency preserves non-seedable requirements.

Example Create Itinerary capabilities: login_salesforce, create_contact, search_tour, select_package, configure_room, configure_protection_plan, configure_bedding, create_itinerary. Absence of Modify Booking must be recorded as a gap, not treated as coverage of that bug.

## TestIntent and ReproductionPlanner (conceptual)

TestIntent preserves the user's reproduction or exploration goal, reported steps, expected/actual behavior, exact values, constraints, and selected project/environment context. Bug-to-test mapping is not always 1:1.

Place ReproductionPlanner between intent interpretation and execution. It maps steps and inputs to existing capabilities, prefers one complete existing test/workflow, identifies reusable setup/preconditions and missing steps, records matching confidence, distinguishes bug-required inputs from automation-owned data, and produces a reviewable plan.

Coverage is separate from confidence:
- **FULL:** existing automation sufficiently covers the workflow. Match → resolve only required external/bug inputs → review → execute → compare observed/reported/expected behavior → BugReproductionResult.
- **PARTIAL:** execute covered setup/preconditions to create useful application state; capture references and hand remaining steps to the tester. This is a valid MVP outcome, not complete reproduction.
- **NONE:** report insufficient automation coverage; do not pretend a weak match is executable coverage.

Never silently convert partial coverage into generated automation. Do not build MVP around an AI browser agent inventing missing steps. AI-assisted gap execution is post-MVP.

A reproduction plan should identify matched automation, covered/missing steps, coverage, confidence/evidence, required inputs and their provenance, setup outputs, review needs, and remaining manual steps. Exact schema and matching thresholds remain to be decided during implementation.

## Input ownership, provenance, and resolution

Existing automation owns everything it already knows how to resolve. Inject or override only values required by user intent or genuinely required externally by that test. A discovered variable is not automatically a generation target.

| Ownership/authority | Required behavior |
| --- | --- |
| BUG_LOCKED | Preserve exact bug value, e.g. TOUR_CODE = BA; AI cannot change it. |
| BUG_CONSTRAINED | Resolve within the bug constraint, e.g. November 2026; never relax it silently. |
| EXTERNAL_INPUT | Resolve/generate an externally required input when appropriate. |
| INTERNALLY_GENERATED | Preserve the test's own Faker/name/email generation; no override by default. |
| GENERATED_RUNTIME | Capture execution output such as CONTACT_ID; never seed it. |
| ENVIRONMENT | Resolve from ProjectEnvironment, e.g. QA base URL. |
| CREDENTIAL / SECRET | Secure runtime reference only; never generate with AI or expose to LLMs, logs, API responses, or plaintext queue payloads. |
| UNKNOWN | Investigate/review; block execution when a required dependency cannot be resolved safely. Never blindly override. |

Keep ownership/authority distinct from discovery location (argument/resource/variable file) and discovery confidence. Preserve source, constraints, and provenance for resolved values. For example:

```text
TOUR_CODE: value=BA, source=BUG, authority=LOCKED
DEPARTURE_DATE: value=2026-11-12, source=ENVIRONMENT/EXISTING_TEST_DATA,
                constraint=November 2026 (only if a valid BA departure exists)
FIRST_NAME: source=INTERNALLY_GENERATED, action=NONE
```

Conceptual source priority: exact bug value → bug constraint → existing test/repository data → QA environment data → deterministic synthetic generation → user review/input if unresolved. A constraint restricts all subsequent lookup/generation; it is not itself a concrete data source. Missing locked values or unavailable constrained inventory must be surfaced, not replaced with invented data.

Distinguish **GENERATE** synthetic data (e.g. an externally required first name) from **RESOLVE** existing valid data (e.g. a BA departure in November 2026). Do not regenerate an internally owned first name in either mode.

## Two data engine modes

**Targeted Replay:** one surgical dataset or application-state preparation plan for a bug. Resolve only the required overrides, such as BA and a valid November 2026 departure; existing automation retains contact generation and setup.

**Strategy Matrix:** explore coverage with a bounded StrategyPlan. For "Generate boundary tests for customer registration," a plan might allocate Happy 2, Boundary 4, Negative 2, Cross-field 2. Strategy Planner decides WHAT cases are needed; Data Engine creates and validates the 10 actual rows. Recommendations alone are not generated datasets. Deliberately negative cases must be checked against their intended rule violations rather than silently repaired into positive cases; detailed validation policy remains an implementation decision.

## Application-state seeding

Test data may be an application state, not just CSV/JSON fields. Existing Create Itinerary automation can create Contact → Itinerary with BA, a valid November 2026 departure, Room, Protection Plan, and Bedding. CONTACT_ID and ITINERARY_ID are execution outputs/reproduction artifacts, not pre-seeded inputs.

For PARTIAL coverage, return environment, created record/reference IDs, data used, setup status, and remaining manual reproduction steps. Successful state preparation is valuable even when the bug remains unverified. Preview must distinguish planned state from state actually created during Phase 2.

## BugReproductionResult (conceptual)

Bug statuses: **REPRODUCED / NOT_REPRODUCED / INCONCLUSIVE / BLOCKED**.

These are separate from runner PASSED/FAILED/ERROR. A Search Tour test expecting results may FAIL because the reported unexpected error occurred; evidence can support bug REPRODUCED. Never derive bug status solely from runner PASS/FAIL. Compare reported, expected, and observed behavior with execution evidence, coverage, and confidence. A successful PARTIAL setup alone does not prove reproduction. Exact status thresholds and manual confirmation policy remain open.

## Canonical acceptance examples (future behavior)

### Full coverage — Search Tour

Pasted bug: (1) log in to Salesforce QA, (2) create a Contact, (3) open Tour Search, (4) enter BA and a November 2026 departure, (5) Search, (6) observe an error.

Assume existing Search Tour automation logs in, generates Contact first/last name/email, creates the Contact, navigates, searches, and validates results. Coverage is FULL. Do not regenerate Contact data. Preserve TOUR_CODE=BA as BUG_LOCKED and departure-in-November-2026 as BUG_CONSTRAINED. Only if valid inventory/test data supplies it, use 2026-11-12. Review and execute the existing test with only these required inputs/overrides.

Return matched automation, confidence, resolved bug inputs, execution result, observed error/result, BugReproductionResult, and evidence/log reference. Runner failure can support REPRODUCED when evidence matches the reported error; failure alone is insufficient.

### Partial coverage — Modify Booking

Pasted bug: (1) log in to Salesforce QA, (2) create Contact, (3) open Tour Search, (4) enter BA and November 2026 departure, (5) Search, (6) select package, (7) select mandatory Room, Protection Plan, Bedding, (8) Create, (9) observe itinerary created, (10) click MODIFY BOOKING, (11) see an error instead of modification options.

Repository contains Create Itinerary covering steps 1–9, but no Modify Booking capability. Coverage is PARTIAL. Do not claim full reproduction or generate Modify Booking automation. Run the existing setup workflow with required resolved inputs.

Example handoff: Setup Automation=Create Itinerary; Setup Result=PASSED; created Contact ID and Itinerary ID; covered steps 1–9; environment and data/evidence references. Remaining manual steps: (10) open/click MODIFY BOOKING, (11) check whether the reported error occurs. Hand the tester the created state and enough information to continue. AI gap execution is future work.

## Discovery confidence

Use:

```text
HIGH
MEDIUM
UNKNOWN
```

- HIGH: explicit test/keyword args.
- MEDIUM: inferred via resource/variable files.
- UNKNOWN: dynamic runtime dependency.

UNKNOWN does not mean irrelevant. Classify whether it is:
- seedable input;
- environment dependency;
- credential dependency;
- secret dependency;
- generated runtime value;
- unresolved runtime dependency.

Only genuinely external/user-intent seedable inputs belong in synthetic generation; explicit arguments are not automatic authorization to override automation-owned data.

## Data engine

### Layer 1 — Schema
Type, nullability, enum, length, regex, min/max.

### Layer 2 — Field generation
Faker, fixed, boundary, invalid, null, duplicate, regex-derived.

### Layer 3 — Cross-field rules
Examples:

```text
country=US => state required
age<18 => guardian required
```

### Layer 4 — Relational graph
Parent-child ordering, foreign keys, generated IDs, future cleanup policy.

Avoid LLM-only validation.

## Strategy planning

Never generate an unbounded Cartesian product.

Create a bounded StrategyPlan.

Example:

```json
{
  "max_cases": 20,
  "happy": 4,
  "boundary": 6,
  "negative": 5,
  "cross_field": 3,
  "relational": 2
}
```

## Immutable artifacts

Track:
- dataset ID;
- seed;
- generator version;
- schema/contract version;
- cross-field rule version;
- repository commit;
- registry version.

Suggested structure:

```text
/workspace/runs/{execution_id}/
    data/
    logs/
    reports/
    screenshots/
    traces/
    metadata.json
```

Use configurable workspace path logic. Never write generated run data into the customer working tree, such as `./tests/data/generated_data.csv`. Finalized artifacts are immutable; retain resolved-value provenance and evidence references in metadata.

## ExecutionContext

Build one context before invoking a runner.

It should identify:
- execution;
- project;
- repository;
- exact source commit;
- registry version;
- test;
- environment;
- role;
- credential reference;
- dataset;
- runner config;
- artifact workspace.

Do not pass raw secrets through Redis.

## RunnerAdapter

Avoid repeated `if framework == ...` branches.

Use:

```python
class RunnerAdapter:
    async def prepare(self, context): ...
    async def execute(self, context): ...
    async def collect_results(self, context): ...
    async def cleanup(self, context): ...
```

Initial adapter: `RobotRunnerAdapter`.

Target flow: ExecutionContext → Execution Orchestrator → RunnerAdapter → RobotRunnerAdapter. Do not call `robot.run()` throughout application services.

Execution modes: SEQUENTIAL, FRAMEWORK_MANAGED, PLATFORM_PARALLEL (future). Local Phase 2 defaults to sequential invocations when the platform manages individual rows. If a test accepts a complete CSV/JSON dataset and iterates internally, preserve that framework-managed invocation. Do not implement platform parallelism in the initial local MVP.

## ExecutionResult

Normalize framework output before persistence/API/UI.

Statuses:

```text
queued
running
passed
failed
error
cancelled
timed_out
```

Failure classes:

```text
ASSERTION_FAILURE
DATA_FAILURE
ENVIRONMENT_FAILURE
AUTH_FAILURE
TEST_CODE_FAILURE
LOCATOR_FAILURE
INFRA_FAILURE
UNKNOWN
```

Use LLM diagnostics only after deterministic classification.

## Output extraction

Do not hardcode Salesforce record IDs into runner code.

Use configurable extractors:
- regex;
- JSONPath;
- framework parser;
- custom extractor.

## Jira / external triggers

Post-MVP unless explicitly requested.

Future flow requires candidate test, candidate dataset, confidence, policy gate, and idempotency.

## Self-healing

Disabled for MVP.

When restored:

```text
locator failure
→ proposed fix
→ confidence
→ human approval
→ patch/update
```

Never retroactively mark the failed run passed.

Prefer Git patch/branch/PR for customer-owned repositories.

## Change discipline

When implementing:
1. read existing files first;
2. reuse existing code where cleanly possible;
3. make the smallest coherent change;
4. preserve compatibility where practical;
5. add/update tests;
6. explain required migration;
7. do not implement later phases unless required.

## Do not

Do not:
- build all framework adapters now;
- add Jira before core repo/data flow works;
- send secrets to LLMs;
- put raw credentials in Redis;
- mutate the customer repo for generated data;
- store registry only in memory;
- use LLM reasoning where deterministic validation is enough;
- mark self-healed failures passed before approval;
- do a big-bang rewrite of the execution engine.

## Implementation order

Completed/current foundation: authentication, projects, environments, subscriptions/usage, MongoDB, Redis, centralized feature flags, and preserved disabled legacy code. Existing Playwright execution infrastructure remains available in source for future adapter migration; it is not an implemented Playwright repository orchestration adapter.

Next, incrementally:
1. Credential safety remediation.
2. Robot repository scanner.
3. Persistent Test Registry.
4. Canonical TestContract.
5. Input ownership + confidence classification.
6. Capability/step discovery.
7. TestIntent / pasted-bug interpreter.
8. ReproductionPlanner.
9. Targeted Replay Data Resolver.
10. Strategy Planner.
11. Four-layer Data Engine.
12. Dataset/application-state preview.
13. CSV/JSON export.

Phase 2:
14. ExecutionContext.
15. RunnerAdapter.
16. RobotRunnerAdapter.
17. Sequential local execution.
18. Application-state / generated ID capture.
19. Normalized ExecutionResult.
20. BugReproductionResult.
21. Partial-reproduction/manual handoff UI.

After core workflow validation:
22. Jira URL/API connector.
23. Jira webhook/pipeline automation.
24. Playwright repository adapter.
25. Selenium repository adapter.
26. Cloud runners / CI integration.
27. AI failure diagnostics.
28. Human-approved self-healing / Max.

This order is not authorization to implement all items at once or enable flags. Credential safety is unresolved follow-up, not a completed redesign. Application-state planning/preview belongs to Phase 1; actual state creation and ID capture require Phase 2 execution.
## Project-scoped access

Project access uses `ProjectMembership` records with `ADMIN` and `TESTER` roles. Project creators become active ADMIN members automatically. Existing projects retain `created_by` and receive a lazy ADMIN membership only when that creator accesses the project, so ownership is not guessed. Team setup is optional during onboarding and remains available under Project Settings → Team. Project administration, team changes, environment changes, repository configuration, and project AI configuration require Project ADMIN; active TESTER members can access safe project and AI status metadata.

## Project AI control plane

Project AI configuration uses `LLMGateway → ProviderRegistry → LLMProvider`. OpenAI and Azure OpenAI are the MVP adapters. Another provider should require a new adapter, catalog entry, registration, and tests rather than changes to AI features. The provider catalog supplies non-secret field metadata to one reusable Settings UI.

Each project has at most one active `ai_configurations` document. ADMIN members can test, activate, replace, or remove configuration; TESTER members can read only safe status metadata. Managed mode uses the server's `OPENAI_API_KEY`. BYOK documents contain a `credential_ref`, harmless suffix, and non-secret provider configuration only.

BYOK material is stored through the replaceable `SecretStore` contract. The MVP `EncryptedMongoSecretStore` uses AES-256-GCM with a fresh nonce and project/reference authenticated data. Its 32-byte URL-safe base64 master key comes only from server configuration as `LLM_SECRET_MASTER_KEY`; it is never stored in Mongo. Provider credentials are not returned, logged, placed in Redis, or exposed to prompts. Replacement validates before changing the active configuration, and the old encrypted secret is deleted only after the new configuration is active.

## Platform control plane and Prompt Registry

Platform authorization is independent from customer project authorization. `users.platform_role` is `OWNER`, `ADMIN`, or `NONE`; missing values read as `NONE`. `PLATFORM_OWNER_EMAIL` is a server-side bootstrap that can persist `OWNER` after trusted local or verified Google authentication. It never demotes an existing owner. Platform roles do not grant access to customer `/projects/...` APIs, and Project ADMIN/TESTER membership grants no platform access.

The current platform module is Prompt Management under `/platform-admin`. Future modules are Customers, Customer Onboarding, Subscriptions, Usage, Projects Overview, and Platform Settings; they are documentation targets only.

`PromptRegistry` stores one atomic definition document per prompt key with embedded immutable versions. Only `DRAFT` content can change. Activation atomically marks one version `ACTIVE`, previous active versions `INACTIVE`, and updates `active_version`; reactivating history provides rollback. `BUG_INTERPRETER` is the sole current definition and declares `TestIntentV1` as metadata only. When no database version is active, resolution returns the canonical `CODE_DEFAULT_V1` code fallback. Prompts are platform-managed, contain no credentials or provider/model settings, and have no project overrides.

## AI usage guard and metering

New production AI features must use `AIUsageService` between the feature service and `LLMGateway`:

```text
AI Feature → AIUsageService → LLMGateway → ProviderRegistry → Provider
```

Customer-facing credits are bounded AI operations and are not tokens. The existing `subscription.usage.ai_gen_used` and `subscription.limits.ai_gen_limit` are the canonical used-credit counter and configurable plan allowance. A calendar-month period is stored with the subscription and reset lazily through an atomic Mongo update; no reset cron is required. Commercial allowances remain configurable and are not finalized.

`BUG_INTERPRETER` is the first operation identifier, but no BugInterpreter exists yet. Its default policy costs one credit, permits 20,000 input characters, bounds output at 1,200 tokens, allows one concurrent request, and permits ten requests per 60 seconds. All values are configurable through nested `AI_USAGE__...` settings. The server selects the operation policy, project billing owner, provider mode, provider, model, and allowance.

Mongo atomically reserves credits before provider invocation. Successful inference consumes the reservation. Authentication, configuration, model, and provider rate-limit failures refund it; timeouts, provider-unavailable responses, and unknown failures consume it conservatively because provider work may have occurred. Rejections before invocation consume no credit. Redis counters enforce per-project, per-user, per-operation rate and concurrency limits; concurrency keys have a bounded TTL and are released after success or failure.

Usage records contain operation, project/user identity, Managed/BYOK mode, provider/model, credit outcome, character count, timestamps, and actual provider-reported token usage when available. Missing token usage remains null and does not fail the operation. Records never contain prompts, pasted bug text, API keys, decrypted credentials, or credential references. Managed cost remains null until a reliable centralized price mapping exists; `managed_cost_eligible` is the extension point for a future monthly cost ceiling. BYOK still consumes platform credits and limits, but is not marked as platform provider spend.

## TestIntentV1 and Bug Interpreter

The implemented Phase C path is:

```text
Paste Bug → BugInterpreter → PromptRegistry → AIUsageService
→ LLMGateway → TestIntentV1 validation → Review
```

`TestIntentV1` answers what the user wants tested. It is framework-neutral and contains no repository, test selection, coverage, plan, dataset, or runner information. `PASTED_BUG` is the only current source and schema version `1` is explicit. Expected result, actual result, and reported behavior remain separate. Meaningful missing information is represented as an INFO or WARNING ambiguity; confidence is HIGH, MEDIUM, or LOW.

Explicit environment evidence is preserved without resolving URLs, IDs, browsers, users, or credentials. Optional `user_context` represents an explicitly supplied role, profile, persona, or actor independently from business inputs. One allowed role is `EXACT`; alternatives stated with OR are `ANY_OF` and must remain unresolved; absent actor evidence stays null or `UNSPECIFIED`. Missing expected behavior deterministically adds one INFO ambiguity unless an equivalent ambiguity already exists.

Inputs use three semantics. `EXACT` is an explicit bug value that future components must preserve. `CONSTRAINED` describes a condition within which a later resolver may select a final value; BugInterpreter does not select it. `UNSPECIFIED` identifies a relevant input without a supplied value or constraint and does not invent one. Constraints remain small and generic; a month such as November 2026 is represented as the complete DATE_RANGE from 2026-11-01 through 2026-11-30.

The active platform prompt is a system message and pasted bug text is an untrusted user message. Providers receive a provider-neutral JSON-schema response request. The result must pass JSON parsing, Pydantic validation, and deterministic semantic validation before it is returned. TestIntent is not persisted; only the existing AI usage telemetry is durable. The project Reproduce Bug page ends at review and provides no run, matching, coverage, or data-generation action.

## Canonical TestContract foundation

The existing Mongo `discovered_tests` collection is the canonical Test Registry source of truth. New Robot scans map deterministic discovery metadata into framework-neutral `TestContract` version `1` records with registry and scanner versions, repository/commit identity, test name, file, line, tags, and timestamps. Inputs, runtime dependencies, capabilities, and assertions remain empty, and confidence remains null until later enrichment phases.

`test_id` is deterministic over repository ID, exact source commit SHA, relative file path, and test name, so a changed commit produces a distinct immutable artifact identity. Same-commit rescans replace that commit's rows, removing stale tests. New-commit rescans preserve older commit snapshots, while current API reads are pinned to the repository's current `source_commit_sha`. Existing flat discovered-test rows receive additive contract defaults on read and require no destructive migration.

Step 2 adds deterministic Robot structure to the same contract snapshot: ordered test keyword calls, raw arguments, Resource import evidence, and referenced user-keyword definitions with immediate nested calls. Resource traversal stays inside the repository root and is cycle safe. Resolution explicitly distinguishes resolved, unresolved, built-in/library, and ambiguous calls. Semantic fields remain empty and no AI participates.

Step 2B adds a separate deterministic Playwright Test TypeScript/JavaScript scanner using Python Tree-sitter. A small scanner registry maps Robot and Playwright results into the same TestContract. Generic `source_imports` and `callable_references` fields represent JavaScript/TypeScript modules, functions, async functions, and Page Object methods without forcing them into Robot Resource or keyword semantics. Static Playwright `describe` ancestry supplies collision-safe test identity while preserving the leaf display name. `discovered_tests` remains the only registry, and all structural data stays commit bound.

Step 2C adds the final framework adapter: deterministic Selenium Java discovery using Python Tree-sitter Java. JUnit 4, JUnit 5, and TestNG tests require both recognized test-annotation imports and Selenium evidence. Package/class/method identity, Java imports, methods, Page Objects, simple inheritance, and ordered invocations map into the same generic contract fields used by Playwright. Selenium and assertion calls remain structural only. No further framework adapter or semantic intelligence is included in this milestone.
## TestContract Step 3A — deterministic value provenance

TestContract Step 3A adds bounded deterministic value provenance for the existing Robot, Playwright TypeScript/JavaScript, and Selenium Java adapters. Framework scanners extract syntax-specific bindings and evidence, then a shared framework-neutral builder stores a flat `value_provenance` graph in each commit-bound `discovered_tests` contract. Records connect through `source_ids` and distinguish structural literals, variables, parameters, arguments, assignments, declarations, call results, member references, environment-access expressions, unknown expressions, and traversal limits. Resolution is explicitly resolved, partial, ambiguous, unresolved, or dynamic. Traversal is limited to depth 8 and 256 nodes with cycle protection. Legacy rows default to an empty provenance list. This step does not populate semantic inputs, dependencies, capabilities, assertions, or confidence; it performs no ownership classification, AI inference, matching, planning, data generation, or execution.

## TestContract Step 3B — deterministic value ownership

TestContract Step 3B classifies reachable call arguments from the existing canonical provenance graph. A separate `value_ownership` field records stable ownership IDs, target provenance IDs, category, deterministic status, evidence IDs, reason code, and source location. Literal origins are `STATIC_INTERNAL`, call-result origins are `GENERATED_RUNTIME`, and structural environment access is `ENVIRONMENT`. Conflicting origins remain `UNKNOWN/AMBIGUOUS`; unresolved, dynamic, and traversal-limited evidence remains `UNKNOWN`. The current architecture cannot prove external test-input boundaries or connect repository expressions to execution credential references, so `EXTERNAL_INPUT` and `CREDENTIAL` remain reserved. Classification never uses names, TestIntent, AI, or runtime values. Legacy rows default to an empty ownership list, and scanner versions remain unchanged.
