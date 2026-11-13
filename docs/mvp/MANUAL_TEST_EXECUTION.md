# Manual test design and execution slice

2026-11-13, development implementation. Accepted priorities 1–3: Test Cases table,
shared version-linked result contract and manual result entry; Scenarios receives
the same table treatment. The user additionally accepted selected-case execution
creation with Release/Cycle notes. This is manual testing, not browser automation.

## Journey

1. Project → Scenarios: search/filter coverage, review/approve and retain Edit/Delete.
2. Project → Test Cases: add/generate, inspect steps and expected results in Review.
3. An authorized project member saves and approves an immutable natural-language design version
   (project-admin sign-off is an optional server policy; see the amendment below).
   Pending/stale designs cannot be selected for a new execution. Table approval
   availability is a pointer summary; the service rechecks eligibility on creation.
4. Select up to 10 approved cases on the current catalog page → Create Test
   Execution → enter a title and Release/Cycle details. Only Manual mode is exposed.
5. Test Execution pins every approved version and its specification. For each case,
   Record result collects actual observations and a manual verdict. Passed requires
   every approved step expectation and assertion to be explicitly confirmed.
6. Completed means all selected cases have terminal results; it does not mean Passed.
   Refresh/reopen retains the manifest, per-case results and historical versions.
   A new execution is required to retest a completed case. Standalone attempt APIs
   and histories remain compatible, but result entry now lives in Test Execution.

The original slice below was extended on 2026-11-13: see [ATTEMPT_BUGS](ATTEMPT_BUGS.md)
for local bug drafts/linking, the platform prompt and execution-spec separation.

Historical initial scope: Release/Cycle is bounded free text, not a release-management integration. No bugs,
external issue publication, attachments, recording ingestion, AI calls or browser
jobs are created by this slice. Bug drafting/linking remains the next milestone.

## Approval basis

Existing knowledge-aware review remains authoritative when both product knowledge
and story analysis are enabled. Linked cases cannot bypass review by disabling a
flag. Changes to story/scenario/case/knowledge require a successor review for new
executions. Already-created executions remain historical pinned specifications.

When both knowledge flags are off, `manual_test_results` permits a legacy,
story-based design review with explicit reviewer-authored expectations. The source
scenario must still be approved and exact acceptance-criterion references must
validate. The immutable context identifies `reviewer-authored-expectations-v1` and
has null knowledge/analysis references; no fictitious knowledge approval is invented.
Cases already carrying knowledge/analysis links, or a partially enabled knowledge
configuration, reject this path. This is an explicit manual-development amendment,
not completion of the knowledge-trained Test Design release gates.

## Contracts and persistence

- Canonical models: `app/models/test_result.py`. `test-result-v1` is a final-result
  envelope with mode, adapter, lifecycle, verdict, specification snapshot, executor,
  optional safe environment metadata, actual result and evidence references.
- Public manual input cannot set mode, adapter, snapshot, executor or recorded time.
  The server assigns `manual` / `human-report-v1`. No automated write endpoint or
  automated assertion evaluator is delivered. Future trusted automation adapters
  can use the same result envelope, with separate orchestration/admission contracts.
- `manual_test_executions`: immutable `manual-execution-v1` manifests pin Release/
  Cycle, selected approved versions, mode and optional environment metadata.
- `test_results`: append-only final attempts, separate from approved designs and
  every existing execution/worker store. Legacy raw history remains unchanged.
- Deterministic Mongo `_id` protects execution submission and per-case completion.
  Matching repeats return the original; conflicting reuse rejects. A grouped case
  has one final record, even if another client uses a different request key.
- Recorded time is server-owned. Actual start/end times are unknown; this slice
  does not invent them. Notes/confirmation are human reports, not independent
  machine evidence. Cancelled is a deliberate per-case terminal report.
- Private, no-store APIs authorize project membership before every read/write.
  Environment queries are project-scoped and project only safe metadata. Validation
  responses omit submitted values. This slice has no filesystem/artifact endpoint.
- History pages are bounded to 20 records, catalog summaries to 50 cases and manual
  executions to 10 cases. Summaries aggregate by project/case/mode in Mongo, without
  inventing automated results from legacy statuses. Latest results retain a version
  marker so an older approval is not presented as a current-version result.
- No existing-data migration or usage reset. Manual results do not consume AI credits
  or claim to count toward legacy automated execution allowances. Commercial manual
  quotas, retention/archival and query indexes require explicit follow-up before scale.

## APIs

All below share `/projects/{project_id}/test-results` and require
`manual_test_results` plus `test_generation`:

| Method | Suffix | Purpose |
| --- | --- | --- |
| GET | `?case_ids=TC1,TC2` | Page-local latest manual/automated summaries and approval pointers |
| GET | `/cases/{id}?skip=0` | Eligible approved version, safe environments, attempt history |
| POST | `/cases/{id}` | Immutable standalone or manifest-linked manual result |
| POST | `/executions` | Create a selected-case manual manifest, no browser/queue |
| GET | `/executions?skip=0` | Manual execution list |
| GET | `/executions/{id}` | Pinned manifest and per-case results |

There is no mutation/delete endpoint for saved results/manifests. Testcase deletion
protection includes new result records. Specification corrections create new design
versions; a new manual attempt/execution uses the newly reviewed version.

## Local configuration

Restart the development backend and refresh the UI after changing flags. The private
development environment was updated append-only with these non-secret overrides:

```dotenv
FEATURES__MANUAL_TEST_RESULTS=true
FEATURES__AUTOMATION_EXECUTION_UI=false
FEATURES__TEST_EXECUTION_UI=false
FEATURES__NATIVE_EXECUTION=false
FEATURES__VISUAL_RUNNER_LAB=false
FEATURES__VISUAL_RUNNER_BATCHES=false
FEATURES__APPROVED_VISUAL_RUN_ADMISSION=false
FEATURES__APPROVED_VISUAL_RUN_EXECUTION=false
FEATURES__APPROVED_WORKFLOW_WORKER=false
```

Both new flags default false in code. `automation_execution_ui` is a presentation
gate over Lab, automated execution/history and dashboard/account execution widgets.
It is not an authorization mechanism or an automatic cancellation mechanism.
Existing backend execution gates remain; the local start/worker flags above are
also false. No unrelated running backend/worker was stopped or restarted.

The Test Execution route now exposes manual execution under its own flag even while
the old automation UI flag is false. Visual specification controls are removed from
Test Cases and preserved in the gated automation execution workspace. Case detail
panels are mounted on demand, avoiding review requests for every catalog row.

## Checks and limits

Backend doubles:

```powershell
# From ai-qa-team-api, using the prepared API environment:
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_manual_results.py -q
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_test_design_review.py -q
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_feature_flags.py -q
```

Real development Mongo only, disposable prefixed collections:

```powershell
$env:PYTHONPATH='.'
..\.feature-flags.venv\Scripts\python.exe -X utf8 tests/verify_manual_results_real.py
```

This verifies real Mongo submission contention, result contention, fresh-service
reads/aggregation and scope/immutable completion. Synthetic sources are approved
through the actual review service, with no model calls. It does not verify normal
authentication, a browser-to-real-API journey, multi-host consistency, disaster
recovery or production durability. All fixtures are dropped after verification.
Creation checks case eligibility sequentially, not in a cross-document transaction;
concurrent approval/source changes across multiple cases need further qualification.

UI: use the isolated Next server and `http://feature-api.test` described in
`UI_UX_REFRESH.md`, then:

```powershell
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
$env:PLAYWRIGHT_MODULE_PATH='C:\path\to\existing\node_modules\playwright'
$env:MANUAL_UI_EVIDENCE='F:\ai-qa-team\tmp\manual-ui-evidence'
node --test --test-concurrency=1 tests/manual-test-execution.test.cjs tests/design-review-pages.test.cjs tests/approved-visual-runs.test.cjs tests/story-test-generation.test.cjs
```

### Current verification results

- 11 new manual result/execution checks passed with auth/Mongo doubles: immutable
  versions/results, duplicates/conflicts, Passed confirmation, stale approvals,
  project/environment/feature/authentication denial, summaries, pagination, pinned
  Release/Cycle and manual-only legacy approval without a knowledge bypass.
- Existing design-review (7), feature-policy/history (23) and product-knowledge (8)
  checks passed: 49 distinct backend checks in total. No provider/browser calls.
- Five real development Mongo groups passed: concurrent manifest creation,
  concurrent case completion, fresh-service reads/summary with mixed Passed/Failed,
  scope/immutable completion, and legacy manual approval without knowledge. All
  disposable collections were removed. No normal-login or real-browser/API journey.
- Eleven intercepted browser checks passed in the final combined run. The final
  dialog-polish rerun passed three manual checks plus the account allowance check
  confirming the execution widget stays hidden: 12 distinct UI checks overall.
- TypeScript, changed-file ESLint and Git whitespace checks passed. Screenshots
  were inspected for the table, manual results and desktop/mobile execution view.
- Initial UI attempts failed when the isolated fixture server was absent, then on
  labels/legacy fixture expectations. An isolated history-route 404 was resolved by
  restarting only the task server with a preserved fresh cache; no application route
  was removed or broadened. These failures are not counted as first-attempt success.
- Loaded local non-secret flags were checked: manual results true; automation UI,
  old execution UI, native execution, Lab, batches, admission, visual execution and
  worker false. Product Knowledge and Story Analysis remain false locally; they were
  not silently enabled. Existing knowledge-linked data still needs its review path.

Production, normal development login to the real new endpoints, multi-host source
approval races, retention/archival, large-data index/performance qualification and
future automated adapter writes remain unverified. No production service or browser provider was used for this verification. Publication is recorded by Git/PR history; it does not establish deployed runtime readiness.

## Approval usability and attribution amendment — 2026-11-13

The user requested optional supporting fields and optional project-admin review.
`Add Test Step` replaces `Add design instruction`. Save blockers are listed rather
than leaving a disabled button unexplained. The workflow is edit → save draft →
inspect exact saved content → explicit approval. Unsaved editor changes disable
approval until saved or the saved draft is explicitly reloaded. Historical versions
and exports remain available; approval never starts an execution.

Additional case outcomes, cleanup, acceptance-criterion excerpts and knowledge-rule
links are optional for human approval. Source criteria and approved rules use
checkboxes/statements rather than manually typed IDs. Provided links must still be
valid. Per-step actions and expected results remain mandatory; a manual Passed result
still requires every expected result to be confirmed. The separate human-reviewed
case model allows empty supporting arrays; the AI generation model retains its
stricter assertion/reference requirements. No requirements are silently invented or
automatically approved to fill these fields.

`FEATURES__TEST_DESIGN_ADMIN_REVIEW=false` is the code default and was appended to
the private local configuration. With false, any authenticated project member may
explicitly approve a saved draft; with true, project ADMIN is required. Membership,
current-source validation, stale checks and immutable approvals always apply. The
API returns the effective approval policy/capability for the authenticated member;
the UI does not grant permission based only on a hidden button or platform role.

Approvals retain server-owned user ID, display-name snapshot, project-role snapshot,
approval timestamp and policy. These appear in the review/history UI and exports,
and are copied into new immutable execution/result snapshots. Existing approvals
retain their original ID/time; absent historical display names fall back to the ID.
No backfill or identity rewrite is performed. Repeating approval cannot overwrite
the original approver, display name or timestamp.

Focused commands for this amendment:

```powershell
# API directory, development/test doubles:
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_test_design_review.py -q
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_manual_results.py -q
# UI directory, isolated fixture server as above:
node --test --test-concurrency=1 tests/test-design-approval-ux.test.cjs tests/manual-test-execution.test.cjs
```

Tests distinguish optional member approval from admin-only enforcement, reject blank
step expectations, preserve stricter generation contracts, and check immutable
approver identity against spoofed request data. Browser checks exercise optional
fields, explicit saved-version confirmation, unsaved edits and role-specific actions.

Amendment verification: 10 design-review, 12 manual-result and 23 feature-policy
checks passed with doubles; seven intercepted UI checks passed (four approval UX,
three manual execution), followed by a passing four-check approval rerun after
scroll/focus polish. Five disposable development Mongo groups passed again,
including persisted approver metadata and approval without supporting arrays.
Fixtures were removed; real login and production were not tested. Initial UI
attempts exposed a dynamic textarea-label issue; explicit accessible labels fixed
it before the passing rerun. Earlier section counts remain historical evidence.

## Status and execution-display amendment — 2026-11-13

Canonical review summaries distinguish Draft, In Review (a draft based on the
current approval head) and Approved. Superseded draft branches do not indefinitely
mark an already-approved case In Review. Summary reads project only version status,
parent and identity metadata, not every full saved specification. A legacy execution
status is not promoted to a current design approval. Eligibility is checked separately
when creating executions; the summary is not a multi-document consistency guarantee.

The execution case table uses Result, with green Approved/Passed/Completed text,
red Failed/Rejected and amber review/blocked/in-progress states, plus text labels
in both themes. Completed means all results were recorded, not all cases passed.
Visible internal version/attempt identifiers are removed from execution screens,
while persisted manifests/identities remain unchanged. Latest manual result links
to its execution using a short ID label and the full scoped route. Standalone
attempts do not get fabricated execution links.

Executed By appears per case within the execution, not on the Test Cases catalog.
Manual results capture the authenticated record submitter's display name and stable
user ID. Repeat submission preserves the original identity, including after a
profile rename. The browser cannot submit executor identity fields. Historical
records without a saved name show Name not recorded; no identity backfill occurs.

Final focused backend run passed 55 tests (14 manual results, 10 design review,
23 feature policy and 8 knowledge). Ten table/manual UI checks passed, followed by
four passing manual checks for the final Executed By/completion color/link additions.
TypeScript, focused ESLint and whitespace checks passed. Five real development
Mongo fixture groups passed for the status projection and persistence path; they
are separate from intercepted UI/auth doubles and do not verify production login.

Next priority, accepted by the user after merging this slice: assess production
Vercel navigation/login performance before further product work. Read-only timing
and deployment/observability inspection only; do not change production settings or
perform customer-data/model/browser-execution operations as part of the assessment.
