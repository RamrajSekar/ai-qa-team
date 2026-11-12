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

## Phase 2 — remaining legacy migration

Reviewed remaining code: `app/ai/scenario_prompts.py` builds legacy story/recorder
prompts; `app/ai/prompts.py` supplies legacy framework-specific testcase instructions.
They are not migrated in Phase 1. Preserve their output/caller compatibility and
separate static instructions from dynamic project content before registry migration.
Never register a rendered customer prompt as a shared platform template. Trace all
callers (including legacy generator services) and add contract/authorization tests.
Do not convert legacy code-generation contracts into NLP contracts incidentally.

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
