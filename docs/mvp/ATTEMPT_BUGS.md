# Failed-attempt bugs and execution separation

2026-11-13. Implements the supplied plan's items 2, 4, 5 and 6 (no item 3 was
listed). Story-analysis visibility, knowledge workspace redesign and ingestion
(items 7–10) are not part of this slice.

## Customer flow

Test Cases retains design review/approval and selected-case execution creation.
It no longer offers Record manual result. Test Execution is the result-entry
location. Existing standalone result records and APIs remain intact for compatibility.

Open a manual execution, record a Failed result, then choose Create bug or Link
existing bug in that case's Actions cell. The same actions appear in the failed
attempt's expanded result history. Other verdicts do not offer bug actions; the
backend also rejects nonfailed attempts.

Create bug prefills an editable local draft with pinned steps, expected results,
human-reported actual results, environment name, role/preconditions and Release/Cycle
when supplied. Severity/frequency and missing context are identified as unknown.
Review the fields, confirm the review checkbox and Save bug draft. This saves a
local report, not an external issue. Manual drafting never invokes AI.

Link existing bug accepts an absolute HTTPS URL without URL credentials. The user
must confirm review. No URL is fetched, previewed or published by the backend;
opening it is a separate user navigation with noreferrer/noopener. Inputs are
bounded and rendered as text rather than executable markup.

Draft with AI is explicit and uses AIUsageService → LLMGateway → configured provider,
with the new `BUG_REPORT_DRAFT` operation (one request unit under the existing policy).
It uses saved attempt facts, not unsaved edits, and says it replaces those edits.
It can suggest only a summary and missing-information questions: trusted code keeps
the original steps and expected/actual facts. Generated text is a proposal, not an
assertion of verified truth. Human review is required again before saving.
Quota/provider/invalid-response failures preserve manual drafting. No automatic AI
retry occurs; ambiguous calls may consume allowance under the existing usage policy.

## Prompt governance and safety

Platform Admin → Prompts includes Bug Report Draft (`BUG_REPORT_DRAFT_V1`), using the
existing versioned registry and platform OWNER/ADMIN authorization. Project admins
cannot manage it solely through their project role. Prompt versions cannot change
the strict response schema or bypass trusted checks. Old Bug Interpreter remains.

All routes require normal authentication, project membership and the existing
`manual_test_results` plus `test_generation` gates. Responses are private/no-store.
No credentials or full environment records are loaded for AI. Common labelled
secret/token patterns are masked before model input; this is not general DLP or a
guarantee that arbitrary user-pasted sensitive information can be recognized.
Users must supply nonsensitive observations. No screenshot/media processing,
customer browser execution or external issue service is introduced.

## Additive data and API contracts

- `test_attempt_bugs`: append-only human-reviewed drafts or external links, with
  project, attempt/run, optional execution, testcase and exact version identities;
  authenticated reviewer, timestamps, original source facts and optional AI prompt
  provenance. Deterministic `_id` makes unchanged save retries idempotent; changed
  content with the same key conflicts. It never mutates `test_results` or approvals.
- `test_bug_proposals`: private AI proposals pinned to project/attempt and prompt
  version; no bug is saved until reviewed. A proposal from another project/attempt
  cannot be attached. Links remain with the old failed attempt after a later pass.
- Existing data require no backfill. No migrations or index creation were executed.
  Supporting query indexes, retention/deletion and pagination beyond the bounded
  latest 50 links per attempt require explicit follow-up before scale/customer release.

All endpoints below use `/projects/{project_id}/test-results/attempts/{run_id}`:

| Method | Suffix | Effect |
| --- | --- | --- |
| GET | `/bugs` | Read failed-attempt prefill and saved links; no model call |
| POST | `/bugs` | Save reviewed local draft or HTTPS link |
| POST | `/bug-draft-ai` | Explicit metered summary proposal; does not publish/save a bug |

## Execution controls

Visual Execution Spec authoring is not mounted in Test Cases. Test Execution now
provides a selected-case visual specification panel plus the reusable workflow
library, alongside the preserved admission/start controls. When manual execution
is enabled too, the automation section must be explicitly expanded. All of
`automation_execution_ui`, `test_execution_ui`, `test_generation` and
`approved_visual_run_admission` must be enabled; authoring additionally requires
`reusable_workflows`. Normal flags remain off. Navigation only reads state; model
and browser actions require their existing explicit controls and server checks.
This does not qualify the incomplete execution adapter or its browser reliability.

## Verification

Five new attempt-bug API/service tests, 14 existing manual result tests, 14 AI usage
tests and 13 platform prompt tests passed with database/auth/provider doubles.
They cover version/attempt identity, duplicate/conflicting saves, retained links after
a pass, HTTPS/review validation, project/feature denial, quota failure, invalid AI
output, actual usage reservation and prompt activation/immutability. Existing legacy
prompt/usage tests initially inherited account flags and failed/stalled; their fixture
setup now explicitly selects the legacy scenario, and reruns passed. The initial
stalled run was stopped and is not counted as a pass.

Six intercepted UI tests passed: selected-case manual execution, no standalone
catalog entry, hidden automation, status colors, manual/AI bug drafting and linking,
and gated per-case specification authoring with no navigation-time POST. No live
login, Mongo persistence, provider billing or external URL was exercised.

Commands from `ai-qa-team-api` with the development Python environment:

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_attempt_bugs.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_manual_results.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_ai_usage.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_platform_admin_prompts.py -v
```

UI prerequisites/isolated server: PERFORMANCE_ASSESSMENT.md. From `ai-qa-team-ui`:

```powershell
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
$env:PLAYWRIGHT_MODULE_PATH='C:\Users\ram\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
node --test --test-concurrency=1 tests/manual-test-execution.test.cjs
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
```

Focused changed-component lint, TypeScript and whitespace checks passed. Real
development integration and production qualification remain NOT RUN. No push,
deployment, migrations, external publication or real model/browser calls occurred.
