# TestContract Step 2B Progress

Last updated: 2026-09-18

## Objective

Add deterministic Playwright Test TypeScript/JavaScript discovery and validate the framework-neutral TestContract boundary without semantic inference, AI, or execution.

## Implementation

- Python Tree-sitter parses JavaScript and TypeScript without executing Node or repository code.
- A small scanner registry composes the existing Robot scanner and the Playwright scanner.
- Playwright detection requires a supported test filename plus a static `@playwright/test` test binding and recognizable test call.
- Static `describe` ancestry forms `test_identity`, preventing collisions between equal leaf names in different groups.
- Ordered calls retain raw callee and argument expressions, locations, and explicit resolution status.
- Static imports and generic callable definitions use additive `source_imports` and `callable_references` fields.
- Local/imported functions, async functions, Page Object methods, nested calls, and cycles are resolved through references where deterministic.
- Mongo `discovered_tests` remains the single commit-bound registry.
- Legacy and Robot documents normalize with empty generic structural collections.

## Validation

- Playwright scanner tests: 5 passed.
- Playwright plus existing Robot structural/discovery tests: 22 passed.
- Combined Playwright, Robot, repository, and project-membership suites: 32 passed.
- Isolated feature-flag regression suite: 13 passed.
- Python compilation and `git diff --check` passed.
- Scanner/model/registry paths contain no AI provider, gateway, prompt, or metering imports.

## Status

Step 2B is complete. Step 3 and semantic classification remain separately scoped.

## Strict exclusions

No input ownership, dependency resolution, capability/assertion inference, AI, matching, planning, data generation, browser execution, Jira, diagnostics, or self-healing.
