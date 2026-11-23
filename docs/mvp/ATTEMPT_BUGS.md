# Failed-attempt bugs and execution separation

2026-11-13. Implements the supplied plan's items 2, 4, 5 and 6 (no item 3 was
listed). Story-analysis visibility, knowledge workspace redesign and ingestion
(items 7–10) are not part of this slice.

## Customer flow

Test Cases retains design review/approval and selected-case execution creation.
It no longer offers Record manual result. Test Execution is the result-entry
location. Existing standalone result records and APIs remain intact for compatibility.

Open a manual execution, record a Failed or Blocked result, then choose Create bug
or Link existing bug in that case's Bugs column. The same actions appear in the
attempt's expanded result history. Other verdicts do not offer bug actions; the
backend enforces the same Failed/Blocked allowlist.

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


## Failed and Blocked usability amendment (2026-11-23)

Bug actions are available for Failed and Blocked saved attempts. The execution table
has separate Actions (view/record result) and Bugs columns. Compact bug/link/list
icons open a shared review dialog; other verdicts and unrecorded cases show no bug
actions. Attempt history retains its existing bug section for both eligible outcomes.

The API enforces the same Failed/Blocked allowlist. Blocked previews retain the
blocked verdict and supplied actual result; they are not relabelled as failures.
Project access, explicit human review, append-only attempt/version identity, HTTPS
validation, local-only drafting, metered opt-in AI and no external publication remain
unchanged. Existing historical bug records and source facts are not rewritten.


Verification: production UI build/TypeScript, six isolated attempt-bug API tests
and 20 intercepted-API browser checks passed. Coverage includes both eligible
outcomes, unsupported verdict rejection, explicit human review, idempotency,
local draft/HTTPS linking and opt-in AI with doubles. Desktop Failed/Blocked
layouts and existing mobile execution checks passed. Scoped lint passed with the
existing set-state-in-effect findings excluded. No migration, external bug
publication, live model or production-data test occurred.


## Bug draft fields (2026-11-23)

Bug drafts display Actual result and a required, bounded Environment text box.
Preview prefills the saved attempt's environment name/ID when known; unknown
values remain blank. New draft saves reject missing/blank environments in the
API as well as the UI. External URL linking keeps its existing contract.
Existing drafts without this new field remain readable and are not migrated.
Deploy UI/API together so new draft submissions include Environment.

Bug context remains in backend draft/source facts but is omitted from the editor
and local-draft display. An entered Environment survives explicit AI drafting;
AI does not invent or replace it. The existing review checkbox, immutable attempt
links and explicit metered AI boundary remain unchanged. Icon buttons override
dialog padding and prevent SVG shrinking.

Production UI build/TypeScript, seven isolated attempt-bug tests and 17
intercepted-API browser checks passed. Browser coverage checks required Environment,
retention after AI, hidden context, full-sized dialog icons and Failed/Blocked
flows. Visual captures were inspected. Scoped lint passed excluding the existing
effect-rule findings. No live model, production data or data migration used.


## Copy-ready draft report (2026-11-23)

The draft dialog is titled Draft Bug. Title, required Environment and summary stay
visible; detailed steps/results/missing-information editing is under an optional
foldout. A large read-only report follows the current draft fields, with numbered
steps to reproduce, Environment, Expected result and Actual result (plus title and
summary). Copy report is an explicit clipboard action, not an external issue write
or save. Copy works with incomplete drafts; Environment is required only for
saving. Manual selection remains available if clipboard access fails. Hidden context is excluded from the report.
The two verbose provenance/AI-success notices were removed. Review and save guards
remain unchanged; no automatic AI call or publication was introduced.

Production UI build/TypeScript and seven intercepted-API manual execution browser
checks passed, including copied content, required Environment and retention after
AI for Failed/Blocked. Clipboard was a browser double, not the user's clipboard.
Desktop/mobile captures were inspected. Scoped lint passed with the existing
effect-rule finding excluded. No backend contract or data migration changes.


## Expected outcomes and incomplete copy (2026-11-23)

Bug preview Expected result uses explicit overall assertions when present, otherwise
all per-step expectations. Blank lines and duplicate lines (whitespace/case/terminal
period variants) are omitted without inventing new expectations. Pinned approved
specifications and historical bug records are unchanged. AI drafting reuses these
same supplied outcome facts. Copy report no longer checks mandatory field values;
review and Environment requirements still apply to saving a bug draft.

Production UI build/TypeScript, eight isolated attempt-bug backend tests and seven
intercepted-API manual execution checks passed. Tests verify outcome preference,
fallback, deduplication, source immutability and copying before Environment/review
are supplied. Scoped lint passed with the existing effect-rule finding excluded.
No live model, production data or migration used.
