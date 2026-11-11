# Recording-trained visual QA MVP

Status: authoritative target, approved planning scope from the 2026-10-31 assessment request. This document describes required behavior, not delivered functionality. See [repository evidence](REPO_GAP_ANALYSIS.md), [delivery plan](IMPLEMENTATION_PLAN.md), and [decisions](DECISIONS.md).

## Purpose and relationship to existing work

Deliver a browser-accessible, human-supervised QA service that learns a bounded application module from narrated recordings, obtains approval for knowledge, generates tests from stories and acceptance criteria with that knowledge as context, and executes approved cases visually. Customers write no scripts or selectors. Backend-controlled specialized AI tasks support the workflow; ordinary code controls authorization, approvals, versions, permissions, comparisons, secrets, retries, budgets, and outcomes. No multi-agent swarm, new agent framework, graph database, Obsidian Second Brain, or MAK4I dependency is required.

This target supersedes the prior brownfield-only MVP priority in `AI_QA_TEAM_SKILL.md` and `CODEX_CONTEXT_PROMPT.md` for this delivery track. Their customer-repository safety, exact-commit binding, input-ownership, conservative uncertainty, normalized results, and preservation rules continue to apply. Existing discovery, bug interpretation, legacy test generation, and execution remain assets; repository import is not a prerequisite for this new customer journey. Never silently fill gaps in imported automation; authored visual cases require their own explicit review and approval.

Implemented foundations include project membership, environments, auth, feature flags, static repository discovery/contracts, provider configuration, prompt management, and AI usage infrastructure. [M1A](M1A_DEVELOPMENT_SLICE.md) adds an integrated default-off Windows mechanical smoke lab using isolated Robot/direct WebDriver and fixture coordinates. It does not implement visual AI targeting or business assertions. Training ingestion, approved product knowledge, teach-back and the full visual executor remain targets. Flags and marketing descriptions do not establish readiness.

## Pilot envelope

One pilot customer, one module, 3–5 workflows, at most two application roles, approximately 10–20 approved cases, English narration, recordings initially up to 30 minutes, one validated Chrome configuration, and batches of up to 10 approved cases, with checks within and across batches eligible for concurrent execution in a shared configurable pool (initial development default: five active checks). One isolated container/browser per active check; excess checks queue. Support forms, buttons, links, basic dropdowns, tables, scrolling, and navigation. Assertions cover visible text, field values, statuses, and numbers. Validate the pilot's actual UI widgets before promising coverage.

Final delivery is SaaS with cloud execution and no customer installation. Staging must be reachable through an approved cloud network path. Development proceeds Windows local execution → WSL/Linux validation → GCP execution spike. Headless Chrome is the cloud default; visible local execution is useful for debugging. Session mode is selected before launch; switching within a session is not promised.

## Primary workflow and acceptance criteria

Agreed workflow refinement (2026-10-31; target behavior, not implementation evidence): **Train product knowledge → review/clarify and approve knowledge → add story + acceptance criteria → generate/review/approve tests → execute → review evidence → approve corrections when needed.**

Recordings supply product knowledge; stories and acceptance criteria define test intent and expectations. Retain and adapt story-based Test Generation as the primary specification workflow. Flag conflicts with approved knowledge before generation; unresolved material conflicts block generation until reviewed. Every test version links to its story, specific acceptance criteria and approved knowledge version. Explicit approved expected results are required before execution. Corrections create reviewed successor versions, flag affected tests and preserve prior approvals and historical run references. Teach-back is optional within knowledge review; any browser demonstration still requires approved bounded actions and expectations.

1. **Configure access:** authenticated project admin registers staging origin and approved application-role secret references. Project roles and application roles are distinct. Reject cross-project references and unsupported network destinations. No actual secret values in API responses, Redis, logs, or model inputs.
2. **Upload training:** validate media signature, size, duration, codec and processing limits; store privately. Restricted processing produces timestamped transcript and selected frames. Malformed/oversized uploads fail safely without executing embedded content. Consent, retention and deletion are explicit.
3. **Extract and review knowledge:** propose terminology, roles, business rules, workflows, exceptions and unknowns with recording timestamps/document references. Keep expected, observed, inferred and unknown information separate. Reviewers can inspect source evidence, correct claims, answer clarification questions, reject claims and approve a version. Repeated observation never automatically becomes a requirement.
4. **Optional teach-back within knowledge review:** explain approved understanding with source references, surface unresolved assumptions, and propose a bounded browser demonstration. Obtain approval of its actions and expectations before execution. Demonstration success is not knowledge approval or full test coverage. No unapproved exploratory actions.
5. **Add story and design/review/approve tests:** retain and adapt existing story-based Test Generation. Capture story, acceptance criteria and out-of-scope information; compare them with the selected approved knowledge before generation. Surface conflicts for human resolution; unresolved material conflicts block generation. Generate drafts containing purpose, role, preconditions, data, natural-language steps, structured actions, explicit assertions, cleanup, rule/expectation references, version and approval metadata. Every test version links to a pinned story version, specific acceptance criteria and an approved knowledge version. Every assertion has an explicit expected result grounded in the acceptance criteria or an explicit reviewer-authored expectation approved with the test. Knowledge supplies context and conflict checks; it must not silently add test expectations. Required unresolved inputs block approval/execution rather than receiving invented values.
6. **Approve and execute:** code rejects missing or unapproved expected results and validates the exact approved case, story/acceptance-criteria references and knowledge versions, role, environment, budget and action permissions. Persist the immutable run manifest before dispatch. Execute only the approved specification. Model output is a bounded target/action proposal, never executable code.
7. **Review results:** show assertion-by-assertion evaluation, expected versus observed values, uncertainty, screenshots, action/checkpoint evidence and failure explanation. A reliable contradiction fails the test; insufficient evidence goes to review. All required assertions must be evaluated for a pass.
8. **Correct and retain:** corrections create draft successor versions, require approval and flag dependent cases for review. Prior versions and run references remain unchanged across sessions. Retrieval must use project-scoped approved versions; embeddings are derived indexes, never the source of truth.

Acceptance tests must also show that skipping teach-back does not block knowledge approval, material story/knowledge conflicts prevent generation, missing source/version links prevent test approval, missing expected results prevent execution, and corrections never mutate approved versions. Acceptance tests must cover positive and negative assertions, ambiguous visual evidence, missing prerequisites, mid-run cancellation, a browser crash, duplicate dispatch, a timeout after a consequential submit, malicious page/recording instructions, secret leakage, and cross-project access. Use a versioned representative corpus; agree numerical reliability and cost thresholds before claiming pilot readiness.

## Optional reusable workflows (scope amendment, 2026-11-10)

Users define approved case steps and may link exact approved reusable workflow
versions in order. Login is optional and application-specific. Public-page tests
can use the environment URL without credentials. Credential steps reference the
selected role's secret fields. Inline actions and reusable calls retain explicit
expected results, immutable approvals and dependency review on correction.
See [approved workflows](APPROVED_WORKFLOWS.md) for implemented authoring and
compiled preview, plus remaining runtime/target-authorization gates.

## Bounded parallel batch execution (accepted scope change, 2026-11-02)

Parallel checks within a batch are required MVP scope (revised 2026-11-02).
A batch groups 1-10 cases and does not own a browser/container. Each eligible case
receives its own isolated container/session and competes for a shared global pool.
The initial development default is five simultaneous checks; account/project caps
can be lower. Two batches share that pool, rather than multiplying the global cap.
All five independent checks in one batch must overlap when five slots are available.
Capacity above five requires separate resource/reliability qualification; ten-case
batch size does not promise ten simultaneous browsers. Scheduling remains deferred.

Every case pins approved test/knowledge/configuration versions and has independent
identity, prerequisites, lifecycle, assertion verdict, private evidence, usage,
container ownership and cancellation. Batch lifecycle aggregates cases; completion
is not a business pass. Runs use fresh profiles and establish their own preconditions.
Customer cases with shared data/dependencies must serialize conflicts even if slots
are available. Container isolation does not isolate application records.

Atomically reserve global/account/project/environment capacity and spending, with
fair dispatch across batches/accounts. Mongo is durable truth. Release each slot
only after termination/reconciliation; lease expiry cannot authorize replacement.
Never replay an interrupted case or uncertain action. Batch cancellation stops all
its active containers and cancels queued cases while retaining completed evidence.
Independent failure must not stop unrelated cases. Enforce separate case and batch
budgets and separate concurrency from execution allowance (one chargeable case is
one execution, regardless of parallelism). Synthetic development remains unbilled.

Acceptance: demonstrate five genuinely overlapping synthetic browser sessions in
one batch, one container/session per case, distinct private evidence, capacity and
idempotency races, fair sharing across batches, independent failure, batch
cancellation, interruption/reconciliation without replay and subsequent valid work.
Reject size 0/>10 and arbitrary URLs/code. Preserve existing sequential batch/history
records without rewriting manifests; drain their containers before check dispatch.
Customer conflict locks, entitlements, business assertions, normal-login qualification
and cloud safety are separate gates. Current implementation/evidence lives in
[execution contracts](EXECUTION_CONTRACTS.md) and [M1A](M1A_DEVELOPMENT_SLICE.md).
The current synthetic implementation does not include M1B; the bounded Linux M1B experiment below is now accepted scope.


## Bounded Linux M1B experiment (accepted 2026-11-03; target, not implemented)

Retain five concurrent Linux checks as the MVP target and configurable development
capacity. Do not replace that target/default with a two-check limit. Two checks in
one batch completed concurrently according to the user; that reported observation
is not independent qualification. The latest measured Linux five-case attempt
completed 4/5 after 5/5 preparations. Windows startup reliability and Linux five-way
reliability remain open, with their existing failures preserved.

These open reliability issues no longer block a bounded synthetic Linux M1B
experiment. They still prevent claims of qualified five-way execution, Windows
clean-install readiness and overall M1/pilot readiness. Customer access/security,
cloud and production qualification gates are unchanged.

First milestone: locate one visible button from a current screenshot, return a
bounded structured target proposal, validate it in trusted code and execute the
allowlisted click. The target must not come from fixture coordinates, a DOM selector
or arbitrary script. Multiple plausible targets/unknown target cause a safe stop.

Subsequent bounded milestones: wait for dynamic loading within an explicit deadline;
scroll in limited increments with fresh observations and stale-coordinate
invalidation; evaluate an explicit approved expected result independently of action
success; prove a deliberately wrong expectation fails and ambiguous evidence needs
review. Preserve cancellation, no replay, project isolation and per-check containers.

Temporary target observations may be processed in bounded memory/private scratch
and discarded. Retain selected checkpoints, assertion evidence and failure/ambiguity
images; no claim that all screenshots are discarded or that the current three-image
smoke behavior already implements this policy. Reuse observations only while layout
is stable; grouping safe input actions must not skip assertion evidence. Measure
capture, model, action and artifact-persistence latency separately. Set explicit
observation/scroll/action/model/time/spending/image-memory and retention bounds
before testing. No unlimited image buffers or automatic consequential-action retries.

A functional experiment may exercise one case to isolate behavior; this does not
change the shared five-slot design or qualify concurrency. Only controlled synthetic
sample flows and reviewed server-owned specifications are in this experiment.
Knowledge ingestion, customer stories/credentials/URLs and broad autonomous QA are
not delivered by it. See DECISIONS A14 and the current implementation-plan task.

## Governance contracts

Knowledge/test lifecycle: draft → in review → approved immutable version; rejection/changes return to a draft successor. Preserve approver identity/time, source references, schema version and content identity. Publishing a rule change identifies affected tests; do not silently reapprove them. Each test version pins its story version, specific acceptance criteria and approved knowledge version. Story/acceptance-criteria edits require impact review and test successors rather than silently changing approved tests. A run pins knowledge version, test version, environment identity, application-role reference, model/prompt versions, runner/image/browser/driver versions, limits and evidence manifest. Repository-derived runs additionally pin repository identity and exact commit SHA. Never interpret a discovered contract as approved business knowledge.

Run lifecycle is separate from verdict: queued/running/stopping/terminal infrastructure states versus:

| Verdict | Required meaning |
| --- | --- |
| Passed | Every required assertion evaluated reliably and satisfied. |
| Failed | Reliable evidence contradicts an approved expectation. |
| Blocked | Prerequisite or execution problem prevented completion. |
| Needs review | Evidence or interpretation is ambiguous. |
| Cancelled | Deliberately stopped. |

Navigation success, an empty assertion list, a manual stub, and a completed model response cannot establish Passed. Retain raw legacy statuses in history; do not retroactively reclassify them without evidence. Bug-reproduction verdicts remain a separate domain.

## Execution boundary

Target: Robot Framework → custom Python visual library → HTTPX direct WebDriver client → ChromeDriver → matched Chrome for Testing. The isolated visual runtime must not require Selenium, Playwright or Puppeteer clients, directly or transitively. Robot is the framework; WebDriver is the protocol; ChromeDriver remains necessary. Preserve existing Playwright packages/runtime separately until an explicit migration is approved.

Introduce a `RunnerAdapter` behind an extended execution service/API, with prepare/execute/collect/cleanup and normalized results. Coexistence requires explicit adapter identity, versioned payloads, independent queues/dispatch, capability validation and separate dependency environments; no unsupported mode may fall back to another runner. Do not simply enable `native_execution` to launch the new mode.

Screenshots identify targets; trusted code validates proposal schema, bounds, current screenshot identity, target confidence, allowed action, origin and budgets, then performs WebDriver pointer/key/navigation operations. Reacquire evidence after viewport changes. Verify post-action checkpoints and evaluate assertions independently. Exact text/numeric comparisons use deterministic code over trusted observations where possible; OCR/model uncertainty remains visible. No arbitrary Python, shell, JavaScript, unrestricted Robot keywords or model-generated programs. Cleanup closes driver/browser/profile and uploads evidence on success, failure, cancellation and best-effort shutdown. Do not use recovery that bypasses the behavior under test.

## Security, reliability and operational requirements

Scope all APIs, database queries, vector searches, object access and jobs to authorized project membership; object prefixes alone are insufficient authorization. Use private storage and short-lived authorized access. Runtime resolves role-scoped secrets under least privilege; models receive only redacted observations. Restrict recording processors and browser containers; treat page text, transcripts and frames as untrusted data, not instructions. Network enforcement must cover redirects, DNS changes, subresources, downloads, localhost/private networks and cloud metadata, with explicit approved exceptions for the staging path. Application-level URL validation alone is insufficient.

Driver access is private loopback inside the job, never publicly exposed. Use per-run browser profiles/workspaces, a shared configurable pool with five concurrent Linux check slots by default (one isolated container and browser/session per active check) within enforced slot and spending limits, and no shared cookies. Persist leases/fencing and action intent/checkpoint journals; do not blind-retry consequential actions after ambiguous timeouts. Deduplicate run initiation, support cooperative cancellation and reconcile stale runs/artifacts after process death. Upload artifacts durably before terminal publication; reconcile interrupted uploads. MongoDB is durable truth; Redis is coordination/cache only.

Initial configurable limits: 10 minutes/run, 40 browser input actions, 30 model calls, limited ambiguity retries (proposed starting value: two per target), and per-run/daily/account spending ceilings. These are engineering hypotheses. Count retries and failed model calls against operational budgets. Reserve allowances atomically; platform-failed executions do not consume evaluation entitlement, even when internal provider cost occurred. Log usage, latency, outcome, prompt/model versions and evidence references without secrets or raw sensitive content.

Private GCS, Secret Manager, Artifact Registry and versioned images are proposed cloud components. Benchmark browser CPU/memory and sandbox behavior before selecting resources. Maintain tested browser/driver pairs, canary regression checks and rollback to an earlier image. Define retention for originals, transcripts, screenshots, logs, indexes and backups; deletion must propagate to derived data and handle retained run references explicitly. Generate an SBOM and third-party notices for the exact shipped image, including browser, media and OCR binaries.

## AI and commercial scope

Managed AI first: platform credentials, tested models, metering and enforceable budgets. Early beta BYOK supports only validated provider/model combinations, organization-admin configuration, secure storage, capability checks and rotation/revocation; never silently fall back to platform/provider accounts. Existing project-admin configuration needs an explicit organization ownership decision. Arbitrary endpoints and self-hosted models are deferred.

Evaluation begins on a controlled sample app. Own-app evaluation is invite-only: one project/user, one recording up to ten minutes, up to five generated cases, five bounded executions, seven-day screenshot retention, no scheduling. Platform failures do not consume execution allowance. Public unrestricted browser execution is deferred.

Commercial hypotheses only: $1,000 fixed-scope pilot; approximately $499/month managed and $349/month BYOK. Do not hardcode them as final prices. Full billing is not a pilot prerequisite.

## Deferred scope

Live training/meeting participation; customer-hosted runners/private-network integrations; BrowserStack/Sauce Labs; more browsers/OSs; streaming/takeover; advanced file/native-dialog/drag/drop; general MFA/CAPTCHA; scheduling/high concurrency; arbitrary AI endpoints; multi-agent coordination/fine-tuning; autonomous release approval. Retain related existing features and data unless a separately reviewed migration authorizes changes.
