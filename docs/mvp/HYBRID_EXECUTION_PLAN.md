# Semantic-first hybrid execution plan

Date: 2026-11-11. Status: **planning direction requested by the user; not implemented**.
This plan proposes an explicit amendment to the earlier screenshot-only targeting
constraint. It authorizes no application change, provider experiment, deployment,
feature enablement or migration. An implementation task must apply the amendment
to the contracts and guidance explicitly; do not silently add DOM targeting.

## Outcome and preserved foundations

Customers continue authoring stories, acceptance criteria, natural-language cases
and optional reusable steps. They write no scripts, CSS or XPath. Recordings remain
product knowledge, not executable test definitions. Human approvals, immutable
versions and explicit expected results remain mandatory.

Recommended resolution order:

1. Semantic intent: computed accessible role/name, associated label and scoped
   visible text, verified against current browser state.
2. Stable DOM contracts: approved/discovered stable identifiers or test attributes,
   translated by trusted code into bounded queries.
3. Visual proposals: screenshot/CV/VLM for controls not adequately exposed through
   supported semantics, subject to approved fallback policy and evidence protection.
4. Stop: missing prerequisites → Blocked; unresolved ambiguity → Needs review.

This is a resolution policy, not a sequence of increasingly permissive clicks.
VLM output is probabilistic, not a deterministic fallback. Exact template matching
is repeatable for a given image but is not automatically resilient across renders.
An iframe is not inherently a visual-only component: supported frame switching and
semantic inspection should be evaluated first. Closed shadow roots, unsupported
frames and custom widgets remain capability-specific; do not promise coverage.

Keep Next.js/FastAPI, Mongo truth, existing feature settings, knowledge/story design,
immutable specifications/admissions, private evidence, cancellation and fencing.
Retain the separate Robot/custom Python/HTTPX direct WebDriver runtime and the
BrowserStack-first provider boundary. No Selenium/Playwright/Puppeteer runtime
clients, agent framework, stack rewrite or replacement queue. Existing separate
Playwright UI tests and visual/mechanical prototypes remain intact.

The current merged worker executes only `about:blank` readiness. Its evidence does
not establish any locator strategy or general test execution. See
[WORKFLOW_WORKER.md](WORKFLOW_WORKER.md). Hybrid targeting will not resolve Windows
browser startup, container sandbox or five-way resource/reliability issues.

## Architecture and contracts

Target flow:

`approved case + pinned policy → isolated worker → observe → resolve target → validate → native WebDriver action → checkpoint → independent assertion → private evidence/result`

Introduce small provider-neutral interfaces within the existing runner:

| Boundary | Responsibility |
| --- | --- |
| Browser adapter | Session, bounded element queries/properties, native actions, frame context, viewport, screenshots, cleanup |
| Semantic resolver | Resolve approved intent to one current element with matching role/name/scope and bounded observations |
| Stable-attribute resolver | Use allowed attribute contracts through trusted query builders; no model-generated query execution |
| Visual resolver | Return schema-validated proposals tied to screenshot identity, viewport/frame and freshness |
| Action executor | Enforce action permissions, interactability, budgets and no-replay semantics |
| Assertion evaluator | Evaluate approved expectations independently; preserve reliable contradiction and uncertainty |

Separate intent from the ephemeral element handle or screenshot coordinates. A
proposed structured intent, for illustration only:

```json
{
  "role": "button",
  "name": "Save draft",
  "match": "exact",
  "scope": {"role": "dialog", "name": "Order"},
  "allowed_strategies": ["semantic", "stable_attribute", "vision"]
}
```

The final schema must specify supported roles, scope/frame representation,
match/normalization rules, sensitivity and action/checkpoint expectations. An
English natural-language label alone must not silently become an approved role,
scope or new expectation. AI can propose compilation; reviewers approve material
intent/expectation changes. Optional test IDs are supported, not required customer work.
The target's accessible control role (for example, button) is distinct from the
selected application credential role and the user's project membership role.
Present target intent in ordinary language in the customer review UI.

Pin resolution policy/version, allowed strategies, adapter capabilities and runtime
identity in each new immutable manifest. Record the actual resolver, scoped match,
observation identity, checks, action status and assertion evidence. Re-find stale
handles; do not persist element IDs as durable target identity.

Use additive versioned contracts/explicit schema negotiation at the existing API
boundary. The existing strict v1 parser must not silently acquire new semantics.
Do not auto-reinterpret v1 visual approvals as hybrid approvals. New drafts can
copy old intent for human review and produce successor approved versions. Preserve
old runs, evidence and the current readiness/synthetic adapters. Reuse the existing
contract export/type-generation approach where applicable.
Material target/expectation or permitted-strategy changes require reviewed
successors; compatible resolver bug fixes instead need a pinned runtime release
and regression evidence, without inventing another mandatory customer review stage.

Proposed default-off gate: `hybrid_execution`, using the existing Pydantic system
and corresponding UI types. Apply it to APIs, worker/proposal side effects and UI;
leave existing execution gates independent. No flag is added by this plan.

Planned repository impact (paths below already exist unless marked new):

| Area | Reuse/extend | Planned change |
| --- | --- | --- |
| Contracts/compiler | `ai-qa-team-api/app/models/visual_specification.py`, `app/services/visual_specifications.py` | Versioned target/assertion contracts, reviewed compilation and compatibility checks |
| Admission/API | `app/services/approved_workflow_runs.py`, `app/routes/visual_specification_routes.py`, `app/config.py` | Pin policy/capabilities; separate gates and operation identity; preserve readiness routes |
| Worker | `app/workers/approved_workflow_worker.py` | Dispatch the new operation through explicit capabilities; preserve fencing, cancellation, private protocol and no replay |
| Runner | `visual-runner/workflow_preflight.py` plus new resolver/action/assertion modules | Preserve fixed readiness; introduce bounded native browser methods and fixed approved-specification keywords behind adapter interfaces |
| Authoring/results UI | `VisualStepEditor.tsx`, `VisualSpecificationPanel.tsx`, `ProjectTestCatalog.tsx`, `FeatureFlagsProvider.tsx` | Review semantic intent/expectations, strategy diagnostics and per-assertion outcomes; keep selectors internal |
| Tests/docs | Existing API, isolated runner and separate UI test suites; MVP docs | Contract migration, provider proof, comparative fixtures and explicit readiness/security evidence |

No existing project, story, scenario, dataset, account or execution-history collection
needs replacement. Add version metadata to new records; choose any new resolver
binding/evidence collection only when its ownership/retention model is defined.

## WebDriver/accessibility feasibility gate

Direct WebDriver already supports element discovery/actions and computed
role/name operations. **Computed role/name endpoints require an element handle;
they do not provide a native `getByRole` search or a complete accessibility tree.**
See the [W3C WebDriver interface](https://www.w3.org/TR/webdriver2/).

For the first adapter, evaluate bounded native/tag/attribute candidate discovery,
then validate computed semantics through the actual BrowserStack session. Include
implicit HTML roles and label/name computation, not just literal `role` or
`aria-label` attributes. Avoid per-element RPC scans of an entire page: remote
round trips may erase the expected latency benefit. Measure candidate count and
RPC count; require bounded scope and safe stop when caps are exceeded.

A full accessibility tree is a separate capability. Chrome exposes a
[CDP Accessibility domain](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/),
but remote availability, node-to-WebDriver mapping, protocol/version support and
provider portability need a spike. Do not make CDP or direct browser WebSockets a
required MVP dependency merely to obtain a tree. Initially prefer a portable
WebDriver subset; a later bounded accessibility adapter needs demonstrated value.

Do not assume direct HTTPX supplies framework auto-wait, locator inference or
strict matching. Implement the small required behavior explicitly and test it.
Do not use arbitrary JavaScript or a hidden JS/DOM locator library as a shortcut.
The semantic approach is consistent with established
[user-facing locator guidance](https://playwright.dev/docs/locators); that is design
evidence, not a recommendation to introduce Playwright into this runtime.

## Safety and outcome rules

- Exact unique match in the approved scope; duplicates require approved scope or
  clarification. Do not choose the first DOM match or use vision to conceal a
  conflicting semantic result. Explicit visual disambiguation needs approved cues.
- Check freshness, page/frame identity, visibility, enabled/editable state and
  interactability. Native interaction must respect overlays and normal application
  behavior; no JS click, forced interaction, hidden-field shortcut or backend bypass.
- Wait/scroll only within approved bounds, with fresh observations after layout
  changes. Discovery/read-only retries are bounded and distinct from action retries.
- Fall back only for permitted target-discovery limitations. Never fall back to
  turn an assertion failure into a pass, omit an assertion or bypass behavior under test.
- Never resubmit a click/type/submit through another tier after an ambiguous
  transport timeout. Reconcile or Needs review. Re-finding an element is not proof
  that a previous input did not occur.
- Expected, observed, inferred and unknown remain separate. Learned locator hints
  may be versioned metadata; observing behavior cannot approve a new requirement.
- DOM/accessibility content is untrusted and may contain secrets, hidden values,
  personal data or injected instructions. Collect a minimal allowlist of metadata;
  do not send full page source/trees or credential values to a model. Vision may be
  withheld when image redaction cannot be established. Redact before storage and
  provider use, including errors/redirects/echoed input. DOM is not inherently private.
- Keep tenant/project authorization, provider permissions, allowed origins,
  redirect/subresource/metadata-network restrictions and runtime-only credential
  resolution. A semantic resolver does not solve the existing network/evidence gates.
- Keep model/image/action/RPC/time/storage limits and usage/latency telemetry.
  Preserve current starting run limits as tunable proposals; choose resolver caps
  from the spike, not unsupported performance promises. No runtime model call is
  required for an exact deterministic semantic match.

Assertions must declare their type, scope and observation source: text equality or
containment, field/status/numeric value, visibility, or an actual visual requirement.
Use exact trusted comparisons where possible, with approved normalization and
numeric rules. Hidden DOM text cannot satisfy a visible-text requirement. Content
presence, viewport visibility and visual appearance are distinct assertions.
Use screenshots for visual requirements and selective checkpoint/failure evidence,
not automatically for every action.

Passed requires every required assertion reliably evaluated and satisfied.
Reliable contradiction → Failed; execution/prerequisite problem → Blocked;
ambiguous evidence/interpretation → Needs review; deliberate stop → Cancelled.
Resolver success or completed navigation cannot pass a case.

## Phases and exit gates

Estimates are engineering effort, not commitments: one engineer familiar with
FastAPI, browser protocols and this repository; six focused hours per engineer-day.
No provider calls or implementation are performed by this planning task.

| Phase | Scope/deliverable | Acceptance gate | Effort |
| --- | --- | --- | --- |
| H0 — policy and contracts | Explicitly apply the architecture amendment; version target/action/assertion/policy contracts; define supported portable subset and rollout flag | Reviewable schema examples, rejection tests and v1 compatibility/migration decisions; guides have no conflicting execution instructions | 1–2 days |
| H1 — capability proof | One BrowserStack session using direct HTTPX; native and explicit roles, labels, duplicate buttons, input, rerender, iframe/open shadow capability probes; compare existing vision control | Actual capability/RPC/latency evidence; semantic-only path requires no vision call; unsupported features stop clearly; cleanup works; no client-library fallback | 2–4 days |
| H2 — semantic action interpreter | Integrate scoped resolution, native click/clear/type/navigation and bounded waits/scroll into isolated Robot worker; safe attribute tier | Approved controlled form executes without AI targeting; ambiguity/disabled/covered/stale elements and uncertain submit stop safely; cancellation/no replay verified | 4–7 days |
| H3 — independent assertions | Explicit typed expectations, exact comparisons, per-assertion outcomes and provenance | Positive and deliberate contradiction cases produce correct outcomes; hidden/ambiguous/skipped observations cannot pass | 3–5 days |
| H4 — bounded visual fallback | Reuse useful screenshot/proposal code behind the same resolver interface; generic controlled canvas/custom-control fixture, freshness and image/model budgets | Valid fallback works only when allowed; refusal/ambiguity stops; no switch after uncertain input or assertion contradiction; cost/latency recorded | 4–7 days |
| H5 — protection, UI and qualification | Runtime secret/evidence protection and network gates, strategy-aware UI/evidence, durable refresh/recovery, real manual login flow and comparative benchmark | Success/contradiction/ambiguity/cancel/interruption/stale approvals/cross-project checks; measured evidence and operational limits reviewed before controlled staging enablement | 5–8 days |

H0/H1 precede the general implementation. H3 must precede any case-pass claim.
Do not claim H2 is deployable to customer URLs before H5's security gate. H4 can
remain disabled while the controlled semantic subset is evaluated. If BrowserStack
cannot expose the required subset, record a provider limitation and decide the
narrow adapter/VM alternative; do not silently add a forbidden client or CDP dependency.

Approximate total: **19–33 engineer-days (114–198 focused hours)**, or **4–7 calendar
weeks solo at 30 focused hours/week**. A two-engineer team could target roughly
**3–5 calendar weeks**, with contracts/provider feasibility still on the critical
path. First useful evidence is the 2–4-day H1 spike after H0. These ranges exclude
recording ingestion, full billing, production hosting, general widget coverage and
parallel qualification. Unresolved provider egress/redaction or provisioning can
extend the schedule; this is not an estimate for completing the entire MVP.

## Comparative verification and rollout

Use the same controlled application versions and representative steps for semantic,
stable-attribute and visual paths. Include native forms, duplicate labels, dialogs,
delayed/covered controls, scrolling, rerenders, an allowed iframe/open shadow case
where supported, and one visual-only control. Vary layout/viewport/text independently.

Record first-attempt correct targets, wrong actions, ambiguity stops, failures,
action/submit duplicates, cleanup, median/p95 latency, RPC count, image/model usage
and per-run provider cost. Retain all denominators. Test wrong target candidates
and wrong expected results explicitly. Set numerical release thresholds from a
recorded baseline and pilot requirements; do not invent a reliability percentage
from a handful of successful runs. Any observed wrong consequential action or
duplicate submit blocks qualification until explained and corrected.

Start with one active BrowserStack session and synthetic data. Preserve the five-way
Linux MVP target/configuration and existing unresolved reliability items; validate
concurrency separately after single-session semantics and data isolation work.
Revert by disabling the new mode for new admissions, cancelling/draining its work
and preserving manifests/results. Never automatically fall back to the legacy engine.

Manual normal-login checks may be performed by the user; fixture/double results
must stay separate. No customer credentials or unapproved provider screenshot
processing are required for the initial capability spike. Commit/PR/merge and any
deployment are separate explicit delivery actions.

**Recommended first implementation task: H0 followed by H1**, limited to contracts
and a direct-WebDriver semantic capability proof against a controlled fixture.
Do not start by building a generic accessibility-tree agent or a broad locator SDK.
