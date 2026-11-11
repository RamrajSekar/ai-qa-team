# TestContract Step 1 Progress

Last updated: 2026-09-18

## Objective

Evolve deterministic Robot discovery into the canonical framework-neutral TestContract foundation without adding enrichment intelligence, AI, matching, planning, or execution.

## Completed

- Inspected repository connection, static Robot scanning, persistence, indexes, API authorization, rescan behavior, tests, and UI consumption.
- Chose the existing `discovered_tests` collection as the single Test Registry source of truth.
- Added TestContract version 1 and deterministic registry mapping.
- Added tolerant legacy-row reads with no destructive migration.
- Preserved commit-pinned IDs and current-commit API reads.
- Verified same-commit removed-test replacement and separate new-commit snapshots.
- Focused repository discovery/TestContract suite: 13 tests passed.
- Combined repository discovery and project-membership suites: 23 tests passed.
- Isolated feature-flag regression suite: 13 tests passed.
- Python compilation and diff checks passed.

## Status

Step 1 is complete. The next milestone must begin as a separately scoped change.

## Strict exclusions

No resources, keywords, nested analysis, input ownership, dependency classification, capability/assertion inference, AI, matching, planning, data generation, execution, Jira, diagnostics, or self-healing.
