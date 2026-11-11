# Phase C Progress

Last updated: 2026-09-17

## Objective

Implement only: Paste Bug → BugInterpreter → PromptRegistry → AIUsageService → LLMGateway → TestIntentV1 → review UI.

## Completed

- Read `AGENTS.md`, `AI_QA_TEAM_SKILL.md`, `CODEX_CONTEXT_PROMPT.md`, and the Phase C request.
- Confirmed Phase A, Phase B, and AI usage/metering foundations are present.
- Inspected Prompt Registry fallback/active resolution, AIUsageService, LLMGateway/providers, project authorization, API conventions, sidebar, project routes, API client, and workspace styling.
- Chosen integration: framework-neutral TestIntent models + dedicated BugInterpreter; provider-neutral JSON-schema response request; project-member endpoint; project Reproduce Bug review page.
- Added strict TestIntentV1 nested contracts and deterministic semantic validation.
- Added provider-neutral system prompt and JSON-schema response support.
- Added BugInterpreter using Prompt Registry and AIUsageService only.
- Added `POST /projects/{project_id}/bugs/interpret` with project-member authorization.
- Added fixture-driven backend tests.
- Added Reproduce Bug page, review UI, sidebar link, types, and responsive styling.
- Updated architecture documentation.

## Current status

Production Phase C is verified. The user-context/environment/expected-result semantic refinement and validation are complete.

## Semantic refinement

- Added nullable framework-neutral `user_context` with EXACT, ANY_OF, and UNSPECIFIED selection semantics.
- Roles/profiles/personas remain separate from business inputs and never resolve users or credentials.
- Refined fallback prompt guidance for explicit environment and actor extraction.
- Missing expected results deterministically receive one INFO ambiguity without duplicates.
- Added conditional User Context review UI; absent context creates no UI clutter.

## Production remediation

- Production Test Connection passed because it sends a plain two-token chat completion without structured output.
- Bug interpretation failed because raw Pydantic JSON Schema omitted nullable/defaulted properties from object `required` arrays, while OpenAI strict structured output requires every declared property to be required and uses `null` to express semantic optionality.
- Added provider-neutral strict-schema normalization and retained `chat.completions.create(response_format={type: json_schema, ...})` for OpenAI SDK 2.7.1.
- Provider HTTP 400/422 request rejections now use `PROVIDER_REQUEST_INVALID` instead of the connection-validation message.
- Safe failure logs include operation, provider, model, normalized status/type/code/parameter, structured-output flag, schema name, and usage ID; prompts, bug text, schemas, credentials, and raw output are excluded.

## Next actions

1. Semantic refinement and relevant backend suites: 65 tests passed; isolated feature-flag suite: 13 tests passed (78 total).
2. TypeScript, targeted lint, and production build passed.
3. The protected Reproduce Bug route rendered successfully at a narrow 551 px browser viewport, returned HTTP 200, and showed no Next.js diagnostic badge after a clean reload.
4. Security audit confirmed no TestIntent persistence and no direct provider, secret-store, repository, coverage, planner, data-engine, or execution coupling in the BugInterpreter boundary.
5. Final report remains to be delivered.

## Strict exclusions

No Test Matcher, repository search, coverage classification, ReproductionPlanner, Data Engine, execution, Jira, or TestIntent persistence/history.
