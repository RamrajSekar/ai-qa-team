# QA Agent training — Milestone 2

Local development implementation, 2026-11-14, on `dev` over the accepted uncommitted
Milestone 1 work. No deployment, shared-database activation or ingestion enablement.
[Approval compatibility/cutover requirements](KNOWLEDGE_APPROVAL_COMPATIBILITY.md)
remain mandatory release prerequisites. Milestone 3 is not started.

## Customer experience

The project destination is **QA Agent**, retaining `/projects/{project}/knowledge`.
The existing design system supplies cards, controls, status badges and evidence
dialogs. The journey is Teach → Review → Save for approval → explicit approval.
This is reviewed project memory, not LLM fine-tuning or a new agent entity.

- Teach accepts product notes or a pasted timestamped transcript. Intentional
  submission saves a training review, then automatically extracts proposals once.
- Completed extraction results are persisted. Mount, refresh and navigation only
  read state; they never start/repeat an AI request.
- Review cards support Confirm, Edit, Reject and Clarify. Statements, information
  type, source selection/quote, per-proposal clarification and AI questions remain
  inspectable. Clarify is not automatic approval or requirement creation.
- Valid pending decisions, edits and answers autosave with an acknowledged status.
  Navigation is guarded while edits are unsaved; browser unload warns. Changes
  killed before acknowledgement are not guaranteed durable. Users can explicitly
  reload saved state after a conflict or uncertain save.
- Save requires confirmed/rejected decisions and resolved required clarifications.
  It creates an immutable M1 successor, retaining all unaffected approved rules.
- Saved additions/modifications/removals and total retained rules are shown before
  approval. Members can teach/review/save; project ADMIN approval remains enforced
  by the original API, not merely hidden UI controls.
- Correct rule starts a review pinned to the current approved version. Remove rule
  requires explicit confirmation, an explicit removal draft, then admin approval.
  Rejecting a proposal never removes approved rules.
- Sources, quotes, transcript segments and historical snapshots remain inspectable.
  Story-derived source proposals are preserved as inferred and cannot independently
  validate their own story. Story-only analysis is still M3; current story gates
  were not relaxed.
- Additional training creates another review, not another agent/store. Reopening a
  known source resumes its saved extraction/review rather than charging again.

## Backend and persistence

`knowledge_training_reviews` stores **pending review coordination**, separately
from approved knowledge. Existing source/version collections remain authoritative
for evidence and approved memory. Every read/write route checks project membership
and the existing product_knowledge gate; responses are private/no-store.

The existing knowledge router adds:

- GET/POST `/training`; GET `/training/{review_id}`.
- POST `/training/{review_id}/extract`, `/review`, `/save`, `/rebase`.
- GET `/sources/{source_id}` for scoped inspection beyond the overview window.

Contracts are in `app/models/knowledge_training.py`, coordination in
`app/services/knowledge_training.py`. Pending IDs are project-scoped; Mongo's
built-in unique `_id` prevents duplicate starts for a submitted request ID.
Review writes use compare-and-set revisions, so competing editors get 409 rather
than silently overwrite. Saved reviews are not editable approval snapshots.

Extraction transitions not_started → running → completed or uncertain. A bounded
150-second operation sits inside a 180-second lease. Expired/interrupted work is
marked uncertain on a read; there is no background replay. An explicit uncertainty
retry identifies the attempt and warns about possible additional cost. Concurrent
starts cannot acquire the same extraction attempt. A source created before an
interruption is recovered through server-owned training origin metadata.

Training requests also set SDK retries to zero through server-only LLMRequest
metadata. OpenAI and Azure support this per request; other existing AI tasks and
connection checks retain their defaults. AIUsageService, provider selection,
allowances and platform extraction prompts are reused. No model/provider fallback
or automatic paid replay was added.

Save allocates a server-owned draft ID, permitting recovery after a lost save
acknowledgement. `ProductKnowledge.create_version` gains only an optional internal
identity/idempotent insert path; its merge, citations, explicit parent rules and
approval receipts remain unchanged. Public payloads cannot choose that identity.
The session saves a reference, not a second approved corpus.

If knowledge changed while a review was pending, save fails closed. Explicit
**Review against current knowledge** creates a successor pending review from the
persisted extraction/answers, resets accepted proposals for reconfirmation, and
does not call AI. Removed correction targets require fresh human inspection.
Original pending reviews/history remain intact; there is no silent rebase approval.

## Deployment and limitations

- No data backfill or automatic startup migration. The pending collection is
  additive. Production qualification should add/review a project/created_at index
  for the bounded review listing, plus retention, deletion and storage quotas.
- The page lists the latest 50 training reviews; a known review URL remains
  recoverable through its scoped API. Knowledge overview still lists 100 versions;
  older versions remain accessible by M1's version-read API. A full history browser
  and long-history receipt-read performance remain future qualification work.
- Do not enable this against shared/production storage while old backend writers
  remain. No environment values or unfinished upload/image/media flags were enabled.
- This slice does not implement story-only analysis, provisional generation,
  document upload qualification, transcription, RAG, execution or new AI frameworks.
- Real provider billing/network interruptions, real-login roles, real Mongo M2
  persistence/lease contention and production reliability require separate checks.
  M1 real Mongo evidence remains historical; it is not relabelled as M2 validation.

## Verification commands

From `ai-qa-team-api`, using the existing developer test environment:

```powershell
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*knowledge*.py' -v
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_training_provider_retries.py -v
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_test_design_review.py -v
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_ai_usage.py -v
```

Current backend results: 25 M1 knowledge regressions and 8 disabled-ingestion checks
passed, plus 13 separately rerun training checks. One retry-policy test
covering both supported provider classes passed, 10 test-design compatibility
checks passed, and 14 AI usage checks passed. All use synthetic auth/database/model
fixtures; no external provider or normal development database was contacted.

UI prerequisites: install existing UI dependencies; start an isolated copy/server
with `NEXT_PUBLIC_API_URL=http://feature-api.test` and port 3125. The tests intercept
that API origin and use synthetic cookies/data, not a real login.

```powershell
$env:FEATURE_UI_URL='http://127.0.0.1:3125'
# Set PLAYWRIGHT_MODULE_PATH only when Playwright comes from an external tool installation.
node --test --test-concurrency=1 tests/qa-agent-training.test.cjs tests/product-knowledge.test.cjs tests/story-test-generation.test.cjs
node node_modules/typescript/bin/tsc --noEmit --incremental false
node node_modules/eslint/bin/eslint.js 'src/app/(app)/projects/[projectId]/knowledge/page.tsx' src/components/knowledge/TrainingReview.tsx src/components/knowledge/knowledgeApi.ts src/components/layout/Sidebar.tsx src/components/knowledge/StoryAnalysisPanel.tsx
```

Final browser result: **7 passed**, including five QA Agent journeys plus the
existing story-analysis/staleness/count and story-to-testcase regressions. The
requested create-project → three rules → additional fourth rule → unresolved
clarification → resume/answer → targeted correction journey passed in a real
browser with **intercepted API/auth fixtures**. Member save/admin handoff,
rejection/removal confirmation, uncertain extraction retry and per-proposal
Clarify/answer persistence also passed. The admin check includes a 390px viewport
horizontal-overflow check and source-evidence inspection. This is not a real-login
UI/API/Mongo/provider integration claim.

TypeScript, focused ESLint, Python compile checks and `git diff --check` passed.
The desktop screenshot was inspected; saved reviews show read-only evidence and
changes rather than disabled editing forms. Existing dialogs/design tokens are
reused. Local visual evidence: `tmp/qa-agent-m2/admin-journey.png` (ignored).

Initial browser runs failed due to test selection/timing and two UI issues: retry
completion did not refresh local proposal state, and a saved textarea value changed
its accessible label on resume. Both UI issues were corrected; the final successful
runs are new verification, not reclassified earlier failures. No live provider or
BrowserStack call, normal development database activation or production deployment
was performed.

## Milestone 3 handoff

Await user review. M3 remains story-only analysis, analysis of meaningful stories
without acceptance criteria, knowledge-aware conflict/staleness UX and the smallest
safe provisional-scenario feasibility assessment. No generation safeguard was
weakened or generation implementation changed in M2.


## Files in the M2 slice

New backend files: `app/models/knowledge_training.py`,
`app/services/knowledge_training.py`, `tests/test_knowledge_training.py`,
`tests/test_training_provider_retries.py`.

Extended backend files: `app/routes/product_knowledge_routes.py`,
`app/services/product_knowledge.py` (server-owned draft identity and scoped extraction
retry option only beyond M1), `app/services/ai/base_provider.py`,
`app/services/ai/openai_provider.py`, `app/services/ai/azure_openai_provider.py`
(request-scoped retry control; defaults unchanged).

UI: existing knowledge `page.tsx`, `components/knowledge/knowledgeApi.ts`,
`components/layout/Sidebar.tsx`, `components/knowledge/StoryAnalysisPanel.tsx`
(destination label only); new `components/knowledge/TrainingReview.tsx`.
Browser tests: new `tests/qa-agent-fixture.cjs`, `tests/qa-agent-training.test.cjs`;
updated `tests/product-knowledge.test.cjs` to retain analysis/count regression
coverage while the old editor journey is replaced by the new training journey.
Existing `tests/story-test-generation.test.cjs` was run without changing it.

Guidance: this document, AGENTS.md, PRODUCT_KNOWLEDGE.md, IMPLEMENTATION_PLAN.md and
the compatibility audit's additive writer note. Prior uncommitted M1 changes were
preserved. No new dependencies, execution implementation, deployment configuration
or .env values were changed. Source-control delivery is tracked by the follow-up pull request.


Final status: M2 is implemented and verified within the local synthetic boundary.
The final training rerun passed 13 tests, including concurrent intent submission
and lost extraction-acknowledgement recovery. The final browser run passed all
seven checks; TypeScript and focused lint passed. The task-owned port-3125 server
was stopped. No M3 implementation began. M3 is ready for a separately reviewed
local-development task; shared/production release is still gated on backend
cutover and real service/provider qualification.
