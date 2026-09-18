# TestContract Step 3A Progress

Last updated: 2026-09-18

## Objective

Add bounded, deterministic, framework-neutral value provenance to canonical TestContract records for the existing Robot Framework, Playwright TypeScript/JavaScript, and Selenium Java scanners.

## Implementation

- TestContract version `4` adds `value_provenance`, a flat graph of structural evidence records connected by `source_ids`.
- Evidence kinds describe syntax only: literals, variable references, parameters, arguments, assignments, declarations, call results, member references, environment-access expressions, unknown expressions, and traversal limits.
- Resolution remains conservative through `RESOLVED`, `PARTIAL`, `AMBIGUOUS`, `UNRESOLVED`, and `DYNAMIC` statuses.
- Framework adapters extract bindings and source evidence; the shared provenance builder connects canonical relationships without parser-specific AST logic.
- Resolved callable references align caller arguments with callee parameters for Robot keywords, Playwright functions/methods, and Selenium Java methods.
- Simple declarations, assignments, later reassignments, call results, members, and environment-access expressions are traced without executing repository code or reading environment values.
- Traversal is bounded to depth 8 and 256 nodes. Callable cycles are visited once, and limit evidence is marked `PARTIAL`.
- Provenance is embedded in the existing commit-bound `discovered_tests` document. No collection or API was added.
- Legacy documents without provenance normalize to `value_provenance = []`.

## Versions

- TestContract: `4`
- Test Registry: `test-registry-4`
- Repository scanner: `repository-static-4`
- Robot scanner: `robot-provenance-3`
- Playwright scanner: `playwright-provenance-2`
- Selenium Java scanner: `selenium-java-provenance-2`

## Semantic boundary

Step 3A records where static values came from. It does not classify ownership or business meaning. `inputs`, `runtime_dependencies`, `capabilities`, and `assertions` remain empty, and `confidence` remains null. No AI, matching, planning, data generation, or execution participates.

## Validation

- Provenance, Selenium Java, Playwright, Robot/repository, rescan/commit, and project-membership suites: 43 passed.
- Isolated feature-flag regression suite: 13 passed with UTF-8 console mode.
- Python compilation and `git diff --check` passed.
- Scanner/model/registry paths contain no AI provider, gateway, prompt, or metering imports.

## Status

Step 3A implementation is complete. Step 3B has not started.
