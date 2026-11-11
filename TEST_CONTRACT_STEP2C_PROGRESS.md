# TestContract Step 2C Progress

Last updated: 2026-09-18

## Objective

Add deterministic Selenium Java discovery as the final framework adapter before framework-neutral intelligence work.

## Implementation

- Python Tree-sitter Java parses untrusted `.java` source without compilation or execution.
- Detection requires a supported JUnit 4, JUnit 5, or TestNG `@Test` import plus Selenium WebDriver import evidence.
- Package/class/method identity, ordered calls, raw arguments, imports, and repository-local method references map into the existing canonical fields.
- Local and imported helpers, Page Object fields/local variables, simple inheritance, overload ambiguity, interface dispatch, recursion, and import cycles are handled conservatively.
- Selenium and assertion-library calls remain structural external-library calls.
- Java source participates in non-Git synthetic revision hashing.
- Mongo `discovered_tests` remains the only canonical registry.

## Validation

- Selenium Java scanner and cross-framework architecture tests: 6 passed.
- Selenium Java, Playwright, Robot, repository, rescan, and project-membership suites: 38 passed.
- Isolated feature-flag regression suite: 13 passed.
- Python compilation and `git diff --check` passed.
- Scanner/model/registry paths contain no AI provider, gateway, prompt, or metering imports.

## Status

Step 2C is complete. No additional framework adapter or Step 3 work was started.

## Strict exclusions

No other framework, semantic input ownership, dependency resolution, capability/assertion inference, AI, matching, planning, test-data generation, execution, browser provisioning, Jira, diagnostics, or self-healing.
