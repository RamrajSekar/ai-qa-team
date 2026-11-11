# AGENTS.md — AI QA Team

This repository is being evolved into a **Dynamic Agentic Test Orchestrator & Test Data Engine**.

Before architectural changes, read:

- `AI_QA_TEAM_SKILL.md` (active skill; the `.codex/skills/ai-qa-team/SKILL.md` path is currently absent)
- `CODEX_CONTEXT_PROMPT.md`

## Current MVP posture

AI QA Team is a non-invasive control plane over existing customer automation. Two planned journeys share the foundation: bug reproduction/test-state preparation and QA exploration/strategic datasets.

Existing foundation: auth, projects, environments, subscriptions, MongoDB, Redis, and implemented centralized Pydantic feature flags. Legacy Story, Scenario/Test Generation, Recorder, native execution, and other out-of-scope features remain disabled behind flags; do not delete or casually enable them. Preserve execution history reads and do not consume execution jobs while native execution is disabled.

Robot discovery, persistent Test Registry, contracts, four-layer data resolution/generation, role-aware secret references, and immutable artifacts are target capabilities, not claims of implementation. True discovery/registry/data policy flags do not establish readiness. See the skill for actual defaults and phased roadmap.

## Architectural rules

- MongoDB is persistent source of truth.
- Redis is cache/queue, not durable registry storage.
- Customer repositories are read-only by default.
- Generated run data lives in isolated artifact workspaces.
- Secrets must not appear in Redis, logs, API responses, or LLM prompts.
- Environment and execution runner are separate concepts.
- Bind discovery and execution to an exact repository commit SHA.
- Use framework-neutral domain contracts.
- Put framework execution behind RunnerAdapter.
- Normalize runner results before UI/API persistence.
- Robot Framework is the only repository integration required for the initial MVP.

- Reuse existing automation before creating anything new; never invent missing coverage.
- Distinguish FULL/PARTIAL/NONE coverage. PARTIAL test-state seeding is valuable; never silently generate missing automation.
- Inject only externally required/user-intent inputs; preserve internally generated test data and runtime outputs.
- Preserve bug-locked values exactly; resolve constrained values without violating constraints.
- Treat UNKNOWN dependencies conservatively; review or block when required inputs remain unresolved.
- Distinguish runner results from bug reproduction results; PASS/FAIL alone cannot prove reproduction.
- Robot first; Playwright/Selenium repository adapters are future work.

## Working style

Prefer incremental refactors.

Before editing:
1. inspect existing code;
2. summarize reusable components;
3. identify the smallest safe change;
4. preserve working flows;
5. implement;
6. run relevant tests;
7. report files changed and remaining follow-up.

Avoid broad rewrites unless explicitly requested.
