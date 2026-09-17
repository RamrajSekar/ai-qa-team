# AI QA Team — Codex Repository Change Prompt

You are working in the **AI QA Team** repository.

Your job is to evolve the existing product into a **Dynamic Agentic Test Orchestrator & Test Data Engine** without throwing away the current implementation.

## Primary objective

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

Detailed product contracts and acceptance examples are maintained in `AI_QA_TEAM_SKILL.md`; both documents describe future behavior unless explicitly marked current foundation.

### Greenfield path — existing functionality, disabled initially

```text
Story
  ↓
Scenario Builder
  ↓
Test Generator
  ↓
Generated Test
  ↓
Execution
```

The greenfield features already exist in the repository and must be retained behind feature flags.

---

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

---

## MVP phases and shared architecture

Phase 1 plans Robot discovery (`robot.parsing`), persistent Mongo registry, contracts with ownership/capabilities/confidence, pasted-bug intent interpretation, reproduction planning, targeted data resolution, bounded strategy planning, four-layer data engine, and immutable dataset/state-plan preview and CSV/JSON export. No autonomous execution is required.

Phase 2 adds ExecutionContext → Execution Orchestrator → RunnerAdapter → RobotRunnerAdapter, an isolated workspace, sequential local execution, Robot output.xml/log.html parsing, generated-ID capture, normalized results, and manual handoff. Preserve Mongo execution history and reuse Redis queue infrastructure safely. Actual application-state creation requires this phase.

The shared policy gate considers match confidence, environment restrictions, role/access, and review where required. Secrets, audit, observability, PII masking, and artifact retention remain cross-cutting concerns. Jira/pipeline triggers, diagnostics, and other framework adapters come after core workflow validation.

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

---

## Canonical domain contracts

### TestContract

Use a framework-neutral model similar to:

```python
class TestContract:
    test_id: str
    project_id: str
    repository_id: str
    framework: str
    suite: str | None
    test_name: str
    file_path: str
    tags: list[str]

    inputs: list[InputContract]
    runtime_dependencies: list[RuntimeDependency]
    capabilities: list  # Steps and supporting discovery evidence
    assertions: list  # Expected behaviors

    confidence_score: float | None

    source_commit_sha: str
    registry_version: str
    parser_version: str
```

### InputContract

```python
class InputContract:
    name: str
    data_type: str | None
    required: bool

    source: str  # Discovery location; distinct from ownership
    ownership: str  # See input ownership/provenance above
    provenance: dict
    seedable: bool
    confidence: str

    constraints: dict
    generation_strategy: str | None
```

Possible source classifications:

```text
explicit_argument
resource_file
variable_file
environment
credential
secret
generated_runtime
unknown_runtime
```

Unknown/secret dependencies must not be generated by AI. They may still be mandatory for execution.

---

## Discovery confidence rules

Use:

```text
HIGH
MEDIUM
UNKNOWN
```

Interpretation:
- HIGH: explicit test/keyword arguments.
- MEDIUM: inferred via imported resources or variable files.
- UNKNOWN: dynamic runtime dependency.

Do not treat UNKNOWN as "ignore entirely".

Instead classify dependency purpose:
- seedable input;
- environment dependency;
- credential dependency;
- secret dependency;
- generated runtime value;
- unresolved runtime dependency.

Only externally required/user-intent seedable inputs are candidates for synthetic generation; preserve internally generated data even if discoverable.

---

## Four-layer data engine

### Layer 1 — Schema Contract
Support:
- type;
- required/nullability;
- min/max;
- enum;
- length;
- regex/pattern.

### Layer 2 — Field Contracts
Support:
- Faker;
- fixed values;
- min/max boundary;
- just-below/just-above boundary;
- null;
- invalid format;
- duplicate;
- special characters;
- regex-derived values.

### Layer 3 — Cross-Field Rules
Examples:

```text
IF country == "US" THEN state required
IF age < 18 THEN guardian required
IF account_type == "BUSINESS" THEN ein required
```

Cross-field validation must be deterministic.

### Layer 4 — Relational Graph
Support:
- parent-child dependency ordering;
- foreign-key propagation;
- captured generated IDs;
- future cleanup policy.

Potential cleanup policies:

```text
KEEP
DELETE_ON_PASS
DELETE_ALWAYS
MANUAL
```

Do not overbuild cleanup in Phase 1.

---

## Strategy planner

Prevent combinatorial explosion.

Natural-language requests must yield a bounded plan.

Example:

```json
{
  "max_cases": 30,
  "strategies": {
    "happy": 5,
    "boundary": 8,
    "negative": 7,
    "cross_field": 5,
    "relational": 5
  }
}
```

Targeted Replay starts with a pasted bug and normally resolves one surgical dataset or state-preparation plan. Jira is a later input adapter. Strategy recommendations must be materialized as actual validated rows by the Data Engine.

---

## Persistent registry

MongoDB is the registry source of truth.

Redis is cache/queue only.

Every registry version must be tied to:
- repository;
- branch when applicable;
- commit SHA;
- parser version;
- registry version;
- discovery timestamp.

Never assume a registry generated from commit A is safe to execute against commit B.

---

## Repository safety

Treat customer repositories as read-only by default.

Do not modify committed CSV/JSON/Excel/test files to inject generated data.

Generated data belongs in an isolated artifact workspace, for example:

```text
/workspace/runs/{execution_id}/
    data/
    logs/
    reports/
    metadata.json
```

Use a configurable path rather than hardcoding a POSIX location into business logic.

Track dataset provenance:
- dataset ID;
- seed;
- generator version;
- contract/rule version;
- repository commit;
- registry version.

---

## ProjectEnvironment

Preserve existing environment functionality. The fields and role-aware credential references below are target guidance, not a claim that credential safety remediation is complete.

Environment means target application environment:

```text
DEV
QA
UAT
STAGING
PROD
```

Environment is not the same as runner/execution target.

Keep separate:

```text
environment_id -> QA/UAT/etc.
runner_type    -> robot-local/playwright-local/cloud/BrowserStack
browser        -> chromium/firefox/webkit where applicable
headed         -> true/false where applicable
```

Recommended environment fields:

```text
environment_id
project_id
name
environment_type
base_url
api_base_url
default_browser
default_headed
default_timeout_ms
ignore_https_errors
variables
is_default
is_active
created_by
created_at
updated_by
updated_at
```

Environment type should allow:

```text
local
dev
qa
uat
staging
prod
custom
```

---

## Role-based credentials and secrets

An environment may have multiple credential profiles for role-based testing.

Never put plaintext passwords/tokens into:
- API responses;
- execution history;
- Redis job payloads;
- logs;
- LLM prompts.

Redis jobs should carry only a reference such as:

```text
credential_profile_id
```

The target design resolves secrets in the worker at execution time. Existing credential safety remediation remains the next separately scoped task; do not describe it as implemented.

Do not expand any existing plaintext-secret pattern.

---

## ExecutionContext

Before Phase 2 execution, construct one canonical context.

```python
class ExecutionContext:
    execution_id: str

    project_id: str
    repository_id: str
    source_commit_sha: str
    registry_version: str

    test_id: str

    environment_id: str
    role: str | None
    credential_profile_id: str | None

    dataset_id: str
    artifact_root: str

    runner_type: str
    browser: str | None
    headed: bool | None
    timeout_ms: int
```

Do not pass large mutable environment blobs or raw secrets through Redis.

---

## RunnerAdapter

Do not spread `if framework == ...` logic through execution services.

Use an adapter contract:

```python
class RunnerAdapter:
    async def prepare(self, context): ...
    async def execute(self, context): ...
    async def collect_results(self, context): ...
    async def cleanup(self, context): ...
```

Phase 2 implements:

```text
RobotRunnerAdapter
```

Future adapters may include:

```text
PlaywrightRunnerAdapter
SeleniumRunnerAdapter
```

Do not implement future adapters until requested. Avoid direct `robot.run()` coupling throughout services.

Conceptual execution modes: SEQUENTIAL, FRAMEWORK_MANAGED, PLATFORM_PARALLEL (future). Default local Phase 2 to sequential execution when managing individual rows. Preserve a single framework-managed invocation when the existing test consumes a whole CSV/JSON dataset and performs its own iteration. Initial local MVP does not implement platform parallel execution.

---

## ExecutionResult normalization

Do not expose Robot XML semantics directly to the UI/API.

Normalize runner output into a framework-neutral result.

Suggested statuses:

```text
queued
running
passed
failed
error
cancelled
timed_out
```

Suggested deterministic failure classes:

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

Only use an LLM for diagnostics after deterministic parsing/classification.

---

## Output extraction

Do not hardcode Salesforce IDs inside runner logic.

Use configurable extractors, such as:
- RegexExtractor;
- JSONPathExtractor;
- framework-specific parser;
- custom extractor.

Salesforce record IDs can be one configured use case, not a platform assumption.

---

## Jira / external trigger safety

Jira execution is post-MVP unless explicitly requested.

Future flow:

```text
Jira
  ↓
Intent match
  ↓
Candidate existing test
  ↓
Candidate dataset
  ↓
Confidence
  ↓
Policy gate
      ├── auto-run if safe
      └── review-and-run otherwise
```

Support idempotency/external trigger IDs to prevent duplicate webhook runs.

---

## Self-healing

Self-healing is disabled for MVP.

When reintroduced:

```text
locator failure
→ proposed fix
→ confidence
→ human approval
→ patch/update
```

A proposed fix must not change a failed execution to passed.

For customer-owned repositories, prefer Git patch/branch/PR generation over direct mutation.

---

## Existing code to preserve

Reuse:
- FastAPI;
- authentication;
- subscriptions/usage;
- MongoDB;
- Redis Cloud;
- projects;
- ProjectEnvironment work;
- execution history;
- current Playwright code where it can later become an adapter;
- agent identities where useful.

Do not perform a big-bang rewrite.

---

## Preserved legacy functionality

Feature-flag gating is already implemented; the actual defaults and behavior are documented above. Retain existing Story, Scenario/Test Generation, Recorder, native execution, Playwright runner, worker, StepEngine, and persistence code. Do not re-enable or rewrite it as part of context alignment. Unfinished WebSocket/live-log functionality is not an MVP deliverable; do not infer a dedicated flag that does not exist.

---

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

---

## Coding rules

1. Follow the repository's existing style and module layout.
2. Extend existing routes/services when appropriate instead of duplicating them.
3. Keep worker logic thin.
4. Put framework-specific behavior behind adapters.
5. Keep secrets out of response models and queue payloads.
6. Use `Field(default_factory=list)` / `Field(default_factory=dict)` instead of mutable defaults.
7. Use timezone-aware timestamps.
8. Verify project ownership/access for repository, environment, registry, test, and execution operations.
9. Add/update tests for behavioral changes.
10. Prefer tolerant backward-compatible reads over mass rewrites of old Mongo documents.
11. Do not execute against a repository commit different from the registry commit without an explicit re-scan.
12. Do not silently replace deterministic validation with LLM reasoning.

---

## Working method

Before editing:
1. inspect relevant files;
2. summarize current implementation;
3. identify reusable components;
4. propose the smallest safe change;
5. implement;
6. run relevant tests;
7. report impact.

For every meaningful change, report:

```text
Files changed
Why
Behavior before
Behavior after
Backward-compatibility impact
Tests run
Remaining follow-up
```

The immediate goal is **not** to implement the entire architecture. It is to safely turn the existing repository toward this architecture while preserving working code.
## Project membership and authorization

Authorization is project-scoped through `project_memberships`. Roles are `ADMIN` and `TESTER`, with `INVITED` or `ACTIVE` status. Creation assigns the creator as ADMIN; legacy `projects.created_by` remains the billing/compatibility owner and supports safe lazy backfill. Optional onboarding team setup and Project Settings → Team share the same membership APIs. Centralized `require_project_member` and `require_project_admin` checks protect project-level LLM/BYOK configuration.

## Project-level LLM configuration

The implemented provider-neutral path is `AI feature → LLMGateway → ProviderRegistry → LLMProvider`. MVP adapters are OpenAI and Azure OpenAI. A shared provider catalog describes safe configuration fields and lightweight capability metadata for the API and reusable project Settings UI.

Project ADMIN members manage one active/default `AIConfiguration`; TESTER members receive safe provider/status metadata without management controls. Managed mode resolves the server-managed `OPENAI_API_KEY`. BYOK mode stores only a `credential_ref` in `ai_configurations`. Actual keys are held by `EncryptedMongoSecretStore` using AES-256-GCM and the server-only `LLM_SECRET_MASTER_KEY` (URL-safe base64 encoding of exactly 32 random bytes). The master key must remain stable across deployments and must not be stored in Mongo.

Test Connection returns normalized provider errors without raw responses or credentials. Switching validates the proposed provider before persisting it, retains the current active provider on validation failure, and deletes the old encrypted credential only after successful activation. Disabled legacy generation remains disabled; its compatibility factory is not the preferred path for new AI features.

## Platform control plane

Platform administration uses the dedicated `users.platform_role` values `OWNER`, `ADMIN`, and `NONE`. Existing users without the field resolve to `NONE`. The server-only `PLATFORM_OWNER_EMAIL` bootstrap persists `OWNER` after trusted authentication and never synchronizes or demotes past owners. Platform authorization and ProjectMembership authorization are independent: Platform OWNER has no implicit customer-project access, and Project ADMIN has no platform access. Never add a platform-owner bypass to normal project APIs.

The implemented platform namespace is `/platform-admin`, currently containing the dashboard shell and Prompt Management. Future Customers, Customer Onboarding, Subscriptions, Usage, Projects Overview, and Platform Settings modules remain unimplemented.

## Platform Prompt Registry

`BUG_INTERPRETER` is the only managed prompt. Its definition names `TestIntentV1` as future output-contract metadata; no TestIntent model or BugInterpreter execution exists yet. A single `prompt_definitions` Mongo document embeds prompt versions so activation and `active_version` change atomically. DRAFT versions are editable; ACTIVE and INACTIVE history are immutable. Activation supports rollback and permits at most one ACTIVE version.

Fallback-first initialization performs no startup writes. `PromptRegistry.get_active("BUG_INTERPRETER")` returns the canonical `CODE_DEFAULT_V1` source when no persisted active version exists. Platform OWNER/ADMIN can create a draft from the fallback, edit it, activate it, and reactivate history. Prompt records contain instructions only: no credentials, project overrides, provider selection, model configuration, schemas, analytics, or evaluations.

Next phase integration, not yet implemented:

```text
Project ADMIN / TESTER → Paste Bug → BugInterpreter
→ PromptRegistry.get_active("BUG_INTERPRETER")
→ LLMGateway → TestIntentV1 → Review
```

## AI usage guard and metering foundation

The provider-neutral path for every new production AI feature is:

```text
AI Feature
  → AIUsageService
  → LLMGateway
  → ProviderRegistry
  → OpenAIProvider / AzureOpenAIProvider
```

`AIUsageService` owns the operation policy, input and output bounds, project/user authorization, server-resolved Managed/BYOK mode, monthly credit reservation, Redis rate and concurrency limits, provider invocation, token telemetry, and usage finalization. Feature services must not implement those concerns or call the gateway directly.

Credits represent operations, not tokens. The established `ai_gen_used`/`ai_gen_limit` subscription fields are reused as the canonical monthly customer allowance. Calendar-month metadata supports lazy atomic reset. Successful calls consume reserved credits. Safely identifiable pre-inference provider failures refund them; ambiguous timeout/provider failures consume them. Redis limiter keys are scoped by project, user, and operation and expire automatically.

Provider adapters normalize actual input/output/total token counts. Unavailable usage remains null. `ai_usage_records` stores no prompt/body or credentials. Managed records are marked eligible for future cost calculation, while estimated cost stays null until reliable centralized pricing exists. No dollar ceiling is claimed yet. Commercial allowances and all initial `BUG_INTERPRETER` limits remain configurable.

Phase C must use:

```text
BugInterpreter
  → PromptRegistry.get_active("BUG_INTERPRETER")
  → AIUsageService.execute(BUG_INTERPRETER, ...)
  → LLMGateway
  → TestIntentV1
```

The AI usage foundation originally stopped at this boundary; Phase C now implements the TestIntent model and BugInterpreter described below.

## Phase C — TestIntentV1 and Reproduce Bug review

Phase C now implements:

```text
Paste Bug
  → BugInterpreter
  → PromptRegistry.get_active("BUG_INTERPRETER")
  → AIUsageService.execute(BUG_INTERPRETER, ...)
  → LLMGateway structured response
  → TestIntentV1
  → deterministic validation
  → Review UI
```

Project ADMIN and TESTER members can use `POST /projects/{project_id}/bugs/interpret`. The request accepts only `bug_text`; provider, model, credentials, limits, cost, and prompt version remain server controlled. Prompt Registry fallback and active database versions both work. The prompt is sent with system authority, while the pasted bug is isolated as untrusted user content.

`TestIntentV1` is framework-neutral and answers **what should be tested**. It does not decide how existing automation will satisfy the intent. Ordered workflow steps retain raw evidence. Explicit values are `EXACT` and must be preserved by later components. Conditions and ranges are `CONSTRAINED`; later components may resolve a value only within the constraint. `UNSPECIFIED` marks a relevant input without a supplied value or constraint and must not be treated as generated data.

Expected, actual, and reported behavior remain distinct. Confidence is HIGH/MEDIUM/LOW, and useful uncertainty is carried as INFO/WARNING ambiguities. JSON, Pydantic, date-range, workflow-order, evidence, and duplicate-input rules are enforced before returning a complete intent. Invalid raw model output is never returned.

The UI supports Paste Bug, Interpret Bug, review, source editing, and Interpret Again. There is no TestIntent persistence, repository search, Test Matcher, FULL/PARTIAL/NONE determination, ReproductionPlanner, data generation, or execution in this phase.
