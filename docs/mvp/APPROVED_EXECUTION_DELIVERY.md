# Approved execution delivery gates

Updated 2026-11-11, `dev`. User-authorized sequence: finish knowledge/story design,
complete the seven execution tasks, verify, then create a `dev` → `main` PR and
merge after review. **Execution scope is not complete; merge readiness is not claimed.**

BrowserStack is accepted as the first development provider behind a reusable
adapter. This supersedes its earlier deferred status for this assigned work.
Future VM/Sauce adapters must satisfy the same contracts. Direct WebDriver does
not require Selenium. Hosting changes do not bypass security/assertion controls.

| Task | Current state | Completion evidence still needed |
| --- | --- | --- |
| 1. Durable admission | Saved manifests and separately gated durable readiness dispatch implemented | Real Mongo idempotency/slot contention/fresh-process reads passed; normal-login/API-restart verification remains |
| 2. Isolated worker | Separate readiness worker and isolated Robot/HTTPX runner implemented | Real BrowserStack readiness/cancellation exercised; general approved actions/assertions remain tasks 3/4; no legacy consumers |
| 3. General actions | Not implemented/qualified; hybrid change planned | H0/H1 semantic-first contract/capability proof, then trusted actions with bounded visual fallback; see HYBRID_EXECUTION_PLAN.md |
| 4. Independent assertions | Not implemented for general workflows | Every expectation evaluated; reliable contradiction Failed, prerequisite Blocked, ambiguity Needs review; missing assertions cannot pass |
| 5. Credentials/evidence | Encrypted environment storage exists | Runtime-only resolution, no secret propagation, redaction before provider/storage, echo/redirect cases, private evidence/cleanup |
| 6. UI controls | Existing synthetic controls retained; general admission save/cancel added | General Start/status/Cancel/evidence, durable refresh/history and clear lifecycle/verdict |
| 7. Real verification | Not run for the new general flow | Normal dedicated dev login/UI/API/Mongo/isolated runner/browser; success, contradiction, ambiguity, cancellation, interruption, stale approvals, cross-project artifacts |

## Durable admission

The preview stays `execution_ready=false` and keeps restrictive
`salesforce-sandbox-preparation-v1` URL validation. General authoring is app-neutral;
target expansion and network enforcement remain separate gates. An onboarding URL
alone does not authorize network access.

`POST /projects/{project_id}/visual-specifications/cases/{testcase_id}/{version_id}/runs`
accepts environment/role, exact preview digest and a 32-hex idempotency key.
Requires `reusable_workflows`, `approved_visual_run_admission`, development mode
and membership. UI label: **Save immutable run admission (no execution)**.

`approved_workflow_runs` has a deterministic unique `_id` derived from
project/requester/key. Matching retries return the original; conflicting key reuse
rejects. New admission checks current specification, knowledge/analysis, expanded
workflow versions, sources and environment. Historical manifests remain immutable
after changes; future dispatch must revalidate immediately before launch.

Manifest purpose `approved-workflow-run-v1`, runtime contract
`robot-visual-workflow-v1`, adapter `browserstack-direct-webdriver-v1`. Pins include
approved spec/digest, source digest, knowledge/digest/analysis when enabled, exact
workflow versions/digests, environment revision/digest, URL, role and credential
identity. No raw environment, username/password/token/ciphertext or filesystem path.
Prior preview digest and a distinct keyed manifest digest are retained.

Lifecycle/verdict are outside the manifest. Initial state `prepared`, reason
`GENERAL_WORKER_NOT_ENABLED`, `execution_ready=false`. Membership-scoped
`GET .../visual-specifications/runs/{run_id}` inspects it; `POST .../runs/{run_id}/cancel`
cancels prepared admission without editing the manifest. No capacity is reserved,
browser launched, queue consumed or synthetic/legacy run reinterpreted.

## Worker/security prerequisites

The proposed [hybrid execution plan](HYBRID_EXECUTION_PLAN.md) now defines the
recommended next targeting work. This planning update changes no runtime behavior.
It explicitly addresses the earlier DOM prohibition at H0 instead of silently
adding semantic/selector execution. The security and independent-assertion gates
below continue to apply to every targeting strategy.

Current bounded worker implementation, commands, measured failures/fixes and
verification distinctions are in [WORKFLOW_WORKER.md](WORKFLOW_WORKER.md). Its only
operation is browser readiness on `about:blank`; it does not execute the selected
URL or approved case actions. A ready browser leaves the case verdict Blocked.

Separate API admission, durable worker supervision and isolated runner. Atomically
claim/revalidate access and approvals, resolve scoped runtime references, launch
only configured executables in the isolated dependency graph. Robot exposes fixed
trusted keywords; no generated code, arbitrary keywords, selectors or JavaScript.
Use versioned browser/proposal interfaces, bounded model/action/time budgets,
checkpoints, conservative assertions and no replay after uncertain submit/timeouts.

Before non-synthetic execution approve a dedicated development target and allowed
origins/redirects/subresources. Demonstrate provider-side egress/DNS enforcement;
initial URL validation or checking redirects after navigation is insufficient.
Block metadata/internal/local access. Withhold credentialed screenshots/provider
calls until redaction is verified across typing, errors, redirects and echoed data.
A password field alone is not evidence protection. Keep required sanitized
assertion/failure evidence private and authorized; temporary observations may expire.

## Verification/merge gate

Nine specification/admission tests cover exact pins, idempotency, stale/conflicting
input rejection, access, disabled flags and cancelled-manifest preservation using
doubles. No general worker/browser is exercised. Development Mongo/Redis pings
passed; real writes/restarts and normal-login integration remain unverified.

A dedicated development account/project/environment and permission for synthetic
screenshots at the configured providers were requested. Do not substitute forged
sessions or intercepted fixtures. Record first attempts, verdict/assertion details,
usage/latency, cleanup and failures. The user subsequently authorized a checkpoint commit and PR before tasks 1–7
are complete. That PR must describe unfinished execution work; merging still
requires the applicable verification/review gate. An author cannot approve their
own GitHub PR; required independent review must not be bypassed. PR #1 is now
merged. The user separately authorized committing, creating a PR and merging the
bounded worker/readiness continuation. General execution remains incomplete.
