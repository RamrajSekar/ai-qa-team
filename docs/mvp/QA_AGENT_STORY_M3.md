# QA Agent M3 — Story integration

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
