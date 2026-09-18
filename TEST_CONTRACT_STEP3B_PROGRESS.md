# TestContract Step 3B Progress

Last updated: 2026-09-18

## Objective

Classify who or what provides values used as reachable call arguments using only canonical Step 3A provenance evidence.

## Implementation

- TestContract version `5` adds `value_ownership`, separate from both structural `value_provenance` and the unchanged `inputs` field.
- The framework-neutral classifier targets `ARGUMENT` provenance records and follows their bounded `source_ids` graph.
- Ownership categories are `EXTERNAL_INPUT`, `STATIC_INTERNAL`, `GENERATED_RUNTIME`, `ENVIRONMENT`, `CREDENTIAL`, and `UNKNOWN`.
- Literal origins classify as `STATIC_INTERNAL`; call-result origins as `GENERATED_RUNTIME`; environment-access expressions as `ENVIRONMENT`.
- Wrapper evidence such as variables, declarations, assignments, arguments, parameters, and members propagates origin ownership without inspecting names or source text semantics.
- Same-category ambiguous origins retain that category with `AMBIGUOUS` status. Conflicting categories become `UNKNOWN/AMBIGUOUS`.
- Dynamic, unresolved, cyclic, and traversal-limited evidence remains conservatively `UNKNOWN` with a machine-readable reason.
- Member access can inherit a runtime-produced base as `GENERATED_RUNTIME/PARTIAL`; arbitrary object reconstruction is not attempted.
- Ownership IDs are deterministic `OWN...` hashes, and every resolved classification retains supporting provenance IDs.
- Classification runs during canonical TestContract construction and is stored in the existing commit-bound `discovered_tests` document.
- Legacy documents normalize to `value_ownership = []`; no migration or additional collection is required.

## Explicitly unsupported classifications

The current scanner evidence does not prove an externally supplied test boundary, so `EXTERNAL_INPUT` remains reserved and uncertain parameters classify `UNKNOWN`. Existing environment credentials and AI BYOK secret references do not provide a safe identity link to repository provenance, so `CREDENTIAL` also remains reserved. Environment access, including password-named keys, classifies `ENVIRONMENT` rather than `CREDENTIAL`.

## Versions

- TestContract: `5`
- Test Registry: `test-registry-5`
- Repository scanner: unchanged at `repository-static-4`
- Robot scanner: unchanged at `robot-provenance-3`
- Playwright scanner: unchanged at `playwright-provenance-2`
- Selenium Java scanner: unchanged at `selenium-java-provenance-2`

## Validation

- Ownership, provenance, Selenium Java, Playwright, Robot/repository, rescan/commit, and project-membership suites: 51 passed.
- Isolated feature-flag regression suite: 13 passed with UTF-8 console mode.
- Python compilation and `git diff --check` passed.
- Ownership/model/registry/provenance paths contain no AI provider, gateway, prompt, or metering imports.

## Status

Step 3B implementation is complete. Matcher and planning work have not started.
