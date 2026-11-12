# Platform-managed QA prompts

## Phase 1 — implemented 2026-11-11

Platform Admin → Prompts reuses the existing platform-only registry, draft editor,
activation/history and rollback. Project administration does not grant access.
Existing BUG_INTERPRETER remains. Added KNOWLEDGE_EXTRACTION_V1,
STORY_ANALYSIS_V1, SCENARIO_DESIGN_V1 and TEST_DESIGN_V1; the knowledge-aware
services now resolve their active platform version for every request and record
that version through existing usage metering. No database seed or migration is needed:
code defaults apply until the platform administrator publishes a draft.

These are shared task instructions, not shared customer knowledge or model training.
Approved knowledge/story context is independently project-scoped. Output schemas,
reference validation, access control and approval transitions remain application code.
Editing a prompt never changes an existing approved knowledge/test snapshot.
Knowledge extraction already returns clarification questions; a standalone clarification
or teach-back task has not been implemented.

## Backend owner configuration

Set the existing `PLATFORM_OWNER_EMAIL=your-platform-account@example.com` in the
private backend environment, restart the API, then authenticate normally using that
account. Do not commit private environment files. The existing trusted authentication
bootstrap persists OWNER on a matching normalized email; signup/profile payloads cannot
self-promote. Verify `/auth/me` reports the platform role before opening the admin menu.
Changing/removing the environment value does NOT revoke an already persisted role;
role revocation needs a deliberate authorized database/admin operation. Project roles
remain separate. Existing platform ADMIN roles also retain access.

## Phase 2 — legacy migration implemented 2026-11-12

Added `LEGACY_STORY_SCENARIOS`, `LEGACY_RECORDING_SCENARIOS` and
`LEGACY_TESTCASE` to the same platform-only registry. Story and browser-recorder
scenario routes resolve the selected version; request metadata and new scenario
records retain its identity. This preserves legacy usage accounting, not a new
dollar budget or a claim that the legacy gateway is fully metered.

Customer context stays outside the shared registry. Allowlisted `{{name}}` slots
are substituted once, with no eval, script execution or general template engine.
Saving/activating templates rejects missing or unknown slots. Existing output fields,
complexity instructions and fallback text are covered by synthetic golden fixtures
from the pre-migration implementation. Whitespace around the unused testcase helper
is normalized. Published content remains immutable; rollback changes the active
pointer. Knowledge-aware scenario/testcase generation continues to use its separate
NLP contracts, not these legacy framework-specific instructions.

`app/ai/prompts.py` has no current runtime callers. Its preserved template is editable
in the admin UI, but editing it does not affect current NLP generation. No unused
code path was enabled. Existing deterministic `generate_playwright_test` is code,
not an LLM prompt, and stays unchanged. The generic AIManager facade accepts caller
prompts and has no embedded domain template. Bug Interpreter was already managed.
Isolated execution behavior was not changed; execution-specific prompt work remains
part of the held Execution MVP, not this Test Design migration.

Prompt validation responses now omit submitted input. Admin UI lists required
placeholders, reports load/save failures, blocks activation of unsaved edits, and
requires explicit activation confirmation. No customer prompts are stored by this
migration. Registry defaults need no seed or automatic migration.

## Phase 3 — controlled preview and release qualification

Add a bounded synthetic-only preview with existing metering and explicit model-call
confirmation; compare draft and active outputs before activation. No preview/model
call is implemented in Phase 1. Add UI authorization regression and real development
login/Mongo checks. Recording ingestion still requires private storage and is unrelated
to prompt editing. Execution MVP remains on hold.

## Verification

Commands from `ai-qa-team-api`:

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_platform_admin_prompts.py -q
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_product_knowledge.py -q
```

Phase 1: 13 platform tests and eight knowledge tests passed with database/auth/provider
doubles. TypeScript check passed; no real AI, browser, login or Mongo integration was
performed. Earlier development attempts failed on an omitted registry registration
and a missing mock collection; both were corrected before passing checks.


2026-11-12 checks: six legacy template/auth/validation tests, 13 platform tests,
eight knowledge tests, four scenario-count tests and seven NLP review tests passed
with doubles. The 23 feature/history tests also passed. TypeScript and focused lint
passed. Nine current-checkout intercepted browser checks passed. Browser evidence and the UI regression commands are recorded in
[UI/UX refresh](UI_UX_REFRESH.md). Real-login/Mongo/provider qualification and
synthetic model preview are still NOT RUN. No normal customer environment changed.
