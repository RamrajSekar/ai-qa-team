# QA Agent review redesign — 2026-11-15

## Follow-up: current-only table and stale-request discard

Historical versions/source lists are no longer rendered in the workspace. Approved
retains its table, with source/topic and Review/Edit/Remove actions. Evidence for a
current rule opens privately through Review. Backend history and reference APIs
remain intact. New approval receipts store the authenticated approver name; retries
preserve that snapshot. Older own-user approvals use a display-only authenticated
profile fallback; unavailable names display a neutral label rather than raw IDs.

The project-authorized revision-checked `/training/{id}/discard` operation cancels
editable training/correction/removal requests, even against stale knowledge, without
publishing, restoring or deleting approved rules. Running extraction must finish or
reconcile first. Saved immutable drafts/approved training cannot be revoked through
discard because approval may race; start an explicit successor to change knowledge.
Discarded requests cannot be rebased. No migration is required; historic receipts
are not rewritten. The original History UI description below is superseded.

Follow-up verification: 51 backend knowledge/training/disabled-ingestion tests and
8 intercepted-API Edge browser checks passed, including the current-only table,
name/topic display and stale removal discard. TypeScript, focused lint, whitespace
and credential-pattern scan passed. These did not use real login, Mongo or AI.

## Scope

Teach, Review (pending count) and Approved tabs reuse the knowledge route, APIs,
pending reviews and M1 immutable approvals. Ask is a separate, unimplemented
milestone. No execution, document/image/media activation or model framework work.

Approved shows only current knowledge in a table with View source, Correct and
Remove. Historical versions remain behind History and sources for pinned evidence;
they are not current requirements. Review groups additions/corrections/removals,
collapses labelled Source excerpts, supports bulk decisions for undecided proposals,
then Review changes → explicit administrator Approve changes. Saving the summary
does not approve it. Members can prepare reviews but cannot approve knowledge.

Extraction adds server-owned instructions to avoid headings, incomplete fragments
and overlapping proposals, including when a platform custom prompt is active.
Exact source validation remains mandatory. No semantic auto-merge, evidence
rewriting or automatic approval is introduced. Real-model extraction quality still
requires representative source evaluation; prompt instructions are not proof of it.

## Autosave and discard

Autosave no longer disables the text fields. An edit sequence protects text entered
while an earlier save is in flight: its response advances the persisted revision,
then the newer local changes are saved next. Navigation remains guarded while dirty;
refresh never starts extraction. Failed/ambiguous requests require reconciliation.

All-rejected reviews (including zero extracted claims) can be explicitly discarded
without answering unused AI questions. The existing save endpoint uses a revision
CAS to close them as `rejected`, clears proposals/questions/answers and private
source-input copy, and never creates a knowledge version or calls AI. It keeps
request identity/digest and completion metadata so repeats cannot trigger a paid
extraction again. Discarded reviews disappear from pending work. This is not a
general source-deletion/purge endpoint: separately stored source evidence is not
deleted, because immutable knowledge may reference it. Approved history remains.

## Removals and compatibility

Removal reviews require a reason. The saved immutable knowledge version includes
`removal_reasons`, covered by its content digest. New direct draft callers must also
provide a reason for each removed rule. Previously approved versions remain readable
and repeated approval remains idempotent. Unapproved removal drafts lacking reasons
must be recreated through a reasoned review; do not mutate or backfill their digest.

The review shows project-scoped scenarios/testcases referencing removed rules or
the selected knowledge version (conservative dependency coverage). It stops rather
than returning an incomplete list if a collection reaches the 10,000-row inspection
bound. Missing granular references in older records remain a qualification limit.
No execution collection, result or manifest is modified. Existing knowledge-version
staleness/generation gates remain authoritative; this slice does not automatically
retire scenarios or overwrite their historical approval/status fields. A dedicated
cross-page impact-status UX is a follow-up if needed.

No data migration or flag change is performed. Deploy the updated API/UI together.
Preserve the all-writer cutover prerequisite in KNOWLEDGE_APPROVAL_COMPATIBILITY.md.
No real shared database or production data was inspected or modified by verification.

## Verification

Commands use the existing isolated environments described in QA_AGENT_TRAINING_M2.md.
Backend: `test_*knowledge*.py`, `test_story_analysis_modes.py`,
`test_test_design_review.py` through unittest discovery. Browser: UI-only Playwright
against an isolated port-3125 Next server and intercepted auth/API, using
`tests/qa-agent-training.test.cjs`, `tests/product-knowledge.test.cjs` and
`tests/story-analysis-modes.test.cjs`. New browser regressions deliberately delay an
autosave and type newer text before its response; verify preserved focus, persistence
after refresh, collapsed source evidence and bulk-reject/discard without questions.
Also run TypeScript, focused lint and `git diff --check`.

Results: 48 knowledge/training/disabled-ingestion tests, 5 story-analysis tests and
10 test-design-review tests passed with synthetic database/auth/provider doubles.
The final training-only rerun also passed all 15 tests after the impact-response fix.
All 9 final browser checks passed. An initial 8/9 browser run included a stale test
label (Removal versus Removals); the label was corrected and both the affected suite
and final combined suite passed. TypeScript and focused lint passed, including the
final selected-tab styling and header/count changes. Approved table layout
was visually inspected from a browser screenshot; the regression also checks 390px
overflow. Real login/Mongo/model quality and production activation are outside this
verification boundary. No live AI calls were made.
