# QA Agent M3 — Story integration

Current explicit-mode behavior is described in the 2026-11-16 amendment below;
the original M3 behavior remains applicable to legacy records and callers.

Implemented 2026-11-14 on `dev`, following M1 and M2 (merged in PR #18).
This is local-development implementation, not shared-database activation approval.

## Behavior and boundaries

- A story with a description or acceptance criteria can be analyzed. A title alone
  is insufficient. Missing criteria no longer prevent identifying missing details.
- Without approved knowledge, analysis is explicitly `story_only`, with a null
  knowledge version. It can be reviewed, but cannot authorize knowledge-aware
  scenario/testcase generation. Unsupported knowledge conflicts, claim references
  and invented acceptance-criteria quotations are rejected before persistence.
- With approved knowledge, analysis remains `knowledge_aware`, pins that version
  and preserves independent-source/self-validation checks. Same-story proposals
  cannot validate their originating story.
- Story edits or a change in active knowledge make reviews stale. Approving the
  first knowledge version also makes a previous story-only review stale. Detail
  and list summaries use the same staleness rule. Legacy analyses without a mode
  are interpreted as knowledge-aware; existing records are not rewritten.
- Generation still requires acceptance criteria, a current reviewed knowledge-aware
  analysis and exact approved knowledge. Reviewing findings never approves new
  business rules. Existing project-admin review authorization is preserved.
- The story panel names the analysis basis, exposes clarification questions and
  links approved knowledge only when a version exists. Loading/refreshing never
  initiates AI analysis. Explicit analysis disables automatic provider retries.

The existing Story Analysis platform prompt/output schema is reused. Server-owned
analysis constraints accompany inputs; server validation remains authoritative.
No new agent, framework, collection, endpoint, dependency or ingestion activation.
M1 merge/approval receipts and M2 training persistence are unchanged.

## Provisional scenario feasibility and bounded follow-up

Not implemented in M3. `app/routes/scenario_routes.py` selects knowledge-aware
generation whenever `product_knowledge` is enabled; `KnowledgeTestDesign` then
requires reviewed knowledge context. Its coverage-intent records, approval and
downstream case generation pin knowledge/analysis references. The legacy branch
does not provide a trustworthy provisional-basis contract. Routing story-only
analysis through either branch would mislabel grounding or bypass existing gates.

Smallest safe next slice: add an explicit versioned story-only coverage-intent
contract and separate opt-in generation action; pin story digest and analysis,
label every draft provisional/story-only, require human review, reject knowledge
validation claims and prevent admission to knowledge-aware case generation or
execution. Define explicit promotion/re-review after knowledge becomes available.
Add API/UI/approval/export regression checks before enabling it. Do not disable
product knowledge or reuse the legacy branch as an automatic fallback.

## Verification

Run from `ai-qa-team-api` using synthetic auth/database/AI fixtures:

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_story_analysis_modes.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p 'test_*knowledge*.py' -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_test_design_review.py -v
```

Results: 5 M3 tests, 46 knowledge/ingestion-disabled/training regression tests,
and 10 design-review tests passed. These are service/ASGI tests with doubles,
not real login, MongoDB, supported-model or deployment verification. The earlier
initial M3 run also imported/reran 25 existing tests; the final test module avoids
that duplicate discovery, and the counts above describe the separate final suites.

Browser regression prerequisites/commands follow M2's isolated UI setup. With
`FEATURE_UI_URL=http://127.0.0.1:3125`, a UI server configured for
`NEXT_PUBLIC_API_URL=http://feature-api.test` and installed UI-only Playwright:

```powershell
node --test --test-concurrency=1 tests/story-analysis-modes.test.cjs tests/product-knowledge.test.cjs tests/qa-agent-training.test.cjs tests/story-test-generation.test.cjs
node node_modules/typescript/bin/tsc --noEmit --incremental false
node node_modules/eslint/bin/eslint.js src/components/knowledge/StoryAnalysisPanel.tsx
```

Final results: all 8 browser checks passed (one new story-only review/refresh check,
one existing analysis/count/staleness check, five training journeys and one legacy
story-to-case flow). These used a real Edge browser with intercepted auth/API,
not real login/Mongo/AI. TypeScript and focused component lint passed. Git whitespace
checks passed. A restricted-environment duplicate backend test stalled and was
stopped; the explicit isolated reruns above completed successfully. The task-owned
port-3125 UI server was stopped after verification.

No real model, database or customer data was used. Model quality remains unqualified. Previously
documented browser/execution reliability results were not rerun for this milestone.

## Release prerequisites

No M3 database migration/backfill is required. Deploy the updated API and UI
together before enabling these flags; old APIs reject story-only analysis and old
UIs cannot accurately label it. Preserve the mandatory all-knowledge-writer cutover
in `KNOWLEDGE_APPROVAL_COMPATIBILITY.md`. A single user does not eliminate the old
binary write hazard. Cutover verification is being performed separately by the
owner; this task does not certify it or enable shared/production flags.

## Explicit analysis modes and rule-level comparison — 2026-11-16

The UI now defaults to an explicit **Story clarity (story-only)** selection. Users
may instead choose **Check against product knowledge**, then intentionally submit.
Selecting a mode, opening a page or refreshing never initiates a metered request.

Explicit requests use `analysis_mode=story_only|knowledge_aware` on the existing
analysis endpoint. New records include `analysis_scope_version=1`. Story clarity
sends no knowledge to the model and pins no knowledge identity; only changes to
the story make that explicit review stale. It never authorizes knowledge-aware
generation. Old records and omitted-mode API callers retain their existing basis,
self-validation and staleness rules; no data rewrite or migration is performed.

Explicit knowledge comparisons validate all source references in the project and
exclude individual rules whose stored source originates from the same story.
Current claim evidence has one source per rule; approval does not change that
origin or create independent support. The model receives only eligible claims and
the pinned approved version ID, not change history or clarification fields that
could carry excluded claims. Analyses persist included rule IDs and excluded
rule/source IDs, statements and reasons for display and refresh recovery.

If every rule is excluded or no approved knowledge exists, comparison stops before
AI usage and asks the user to choose Story clarity explicitly. Missing/foreign
source records fail closed. Model findings cannot cite excluded or unavailable
rules. Approvals, immutable knowledge, receipts and project authorization remain
unchanged.

This is analysis only. Generation retains the existing full-context independent-
source gate and never treats a partial comparison or a story-only review as
permission to bypass it. Provisional scenarios, release-aware requirements and
intentional-change approval remain separate follow-ups.

### Explicit-mode verification

- Backend: 10 story-analysis-mode tests, 65 knowledge/Ask/training regressions,
  and 10 test-design review tests passed (85 total, synthetic services).
- Browser: 4 story analysis/count/staleness checks and 9 existing training and
  story-to-test checks passed (13 total, intercepted auth/API, Edge).
- Source-only TypeScript, focused ESLint and Git whitespace checks passed.
- An initial browser attempt hit slow compilation and missing generated modules
  in the disposable UI copy; it was interrupted. The copy's build cache was
  cleared, routes warmed, and all checks above passed on the restarted server.
- No real model, production database, data migration, ingestion or execution
  activation was performed. Existing backend cutover prerequisites remain intact.

### Scenario workspace and status refinement (2026-11-17)

Stories retain clarity review and explicit approval. Generation and manual scenario
creation use the existing Scenarios catalog, with a story-preserving Open Scenarios
button. Requirements for generation is the single normal selector. Duplicate context
and release-authoring forms are removed from this flow; approved legacy releases
remain selectable when available. Existing context records and APIs are preserved.

List and detail share receipt-verified story approval summaries. Knowledge comparison
freshness is separate: approving a story does not make an old comparison current.
Historical findings are collapsed and excluded from current unresolved counts.
Generation safeguards, source independence, project access and immutable history remain.

Verification: 15 intercepted-API browser checks passed for catalog pagination,
edit/delete, protected deletion, manual case design, navigation, release selection,
and admin/member review. Three additional focused browser checks passed for the
moved generation flow and list/detail status consistency. Thirteen focused backend
story approval tests passed, including repeated/concurrent approval and corrupt
manifest rejection; the broader 76-test backend regression set passed earlier.
No live provider, production database, migration or execution was used.


## Story citation compatibility — 2026-11-18

Finding evidence accepts whitespace-only layout differences and stores the exact
matched source excerpt. Wording, punctuation, case and business values are not
normalized. A valid description/title/out-of-scope quote returned in the legacy
criterion_quote field is moved to optional story_quote/story_field and displayed
with its actual source, never as acceptance criteria. Native story_quote citations
are validated against their explicitly named field. Blank criterion quotes become
null; invented/mismatched excerpts still reject the entire result before storage.

Both analysis modes use the same evidence validation. Story-only rejects all
knowledge references/conflicts; knowledge comparison permits only included source
IDs and requires a linked rule for conflicts. Excluded same-story rules remain
unavailable. Server-owned prompt constraints specify nulls and source fields, even
when a platform-saved prompt overrides the fallback. No automatic retry or extra
metered request is introduced; no past record/approval is rewritten or migrated.

The exact rejected provider payload from the user report was not retained, so the
specific triggering field remains unconfirmed. Regression fixtures reproduce the
reported Contact record-type requirements with line-break differences, description
citations, legitimate independent rules, and rejected invented/excluded references.
No production database or live provider was used for these checks.


Validation: 45 backend fixture checks passed (15 analysis-mode/evidence checks and
30 knowledge regressions); four intercepted-API browser checks passed for both
modes, no silent fallback/retry, refresh recovery and distinct story evidence labels.
TypeScript, scoped ESLint and Git whitespace checks passed. The first browser
attempt had no running isolated server; the successful rerun used the restarted
server. Story Clarity uses a generic unsupported AI reference error; knowledge
comparison reports unavailable knowledge references specifically. Existing data,
knowledge isolation, metering and approval safeguards remain unchanged.


## Manual story review — 2026-11-18

Project ADMIN can explicitly Approve manually after reviewing the displayed exact
story and confirming it is clear enough for test design; a note is optional.
An immutable manual_story_approval receipt in requirement_contexts pins the story
and latest analysis snapshot, authenticated reviewer/name/project role/time and
project_admin_manual_story_review_v1 policy. Deterministic _id elects one reviewer
for repeated/concurrent submissions. Input changes fail closed; no record is
rewritten. Existing unresolved material findings/conflicts for the current story
revision block this path, including earlier findings hidden by newer analyses.

Manual approval never creates an analysis, approves knowledge or spends AI usage.
Status is Approved · Manual review; absent analysis remains Not analyzed. Approved
story design contexts can use this authority with no knowledge claims or analysis
identity. Scenarios and cases remain story-only drafts requiring their own review.
New findings/story changes require review again; legacy knowledge-aware paths keep
their existing checks. No migration, execution/media activation or startup backfill.

For stories already approved, the knowledge proposal entry is Add/update knowledge
and final approval is Approve knowledge changes. Those actions still use the
existing proposal/impact review and immutable knowledge successor approval path.

Verification: isolated tests cover no-analysis approval/generation, unchanged AI and
knowledge records, exact snapshot invalidation, repeated/concurrent attribution,
role/project/forged-identity/integrity guards and historical unresolved conflicts.
Existing context, knowledge, combined-change and analysis-mode regression suites
passed. Ten intercepted-API browser checks passed, including explicit confirmation,
member restrictions, refresh recovery and the renamed knowledge actions.
TypeScript/scoped ESLint and whitespace checks passed. No live provider, shared
Mongo database, ingestion or execution was used for verification.


## Approved story knowledge proposals — 2026-11-18

Approved stories (manual or AI-assisted) show Add knowledge and Update knowledge.
Add needs no further form: it faithfully copies approved requirements and reviewed
clarifications into completed-but-undecided QA Agent training review cards, without
AI, extraction, auto-confirmation or knowledge publication. Description and acceptance criteria become review proposals; title and scope
remain inspectable source context. Standalone headings are not invented rules.
Update selects one exact current approved rule and seeds its replacement from the
story into the same review pipeline. Removal remains in QA Agent; the story's new
proposal API accepts only add/update. Existing conflict decisions and historical
change-review APIs remain compatible; old submitted reviews remain inspectable.

Server-owned deterministic source/review/draft identities prevent repeated or
concurrent clicks duplicating drafts. Same approved source and target reopen the
existing review, including completed approvals; discarded requests are not silently
resurrected. Story changes create a new source identity. Base-version conflicts use
the existing explicit rebase review. Source/approval fingerprints are rechecked at
draft save and before new publication, including direct version-approval callers.
Retained historical rules do not block unrelated later knowledge changes. No old
approval, M1 receipt or execution reference is rewritten.

Story-origin evidence is retained and excluded from validation of its own source
story. Add proposals preserve source text across bounded excerpts; source text is
limited to 60000 characters, at most 60 cards. An update must fit the existing
single-rule/source-quote bounds (1200 characters); larger corrections remain in
QA Agent with explicitly focused evidence rather than silently truncated rules.
Both flows require ordinary confirm/review/save and project ADMIN approval before
an approved successor is published; unaffected rules are retained automatically.
No model call, migration, new flag, media ingestion or execution activation.


Verification for approved-story proposals: 76 backend fixture checks passed
(8 proposal, 18 training, 30 knowledge, 15 combined-review and 5 Overview queue).
Ten intercepted-API browser checks passed, covering Add/Update from manual and
AI-assisted approval, QA Agent review routing, unchanged conflict review and manual
approval. TypeScript/scoped ESLint and whitespace checks passed. Long repeated
source text exposed per-chunk deduplication loss in a fixture; deduplication now
applies only to identical whole fragments and the lossless excerpt check passed.
No live model, shared database, media ingestion or execution was used. Existing
knowledge-writer cutover prerequisites remain; no existing-data migration.
