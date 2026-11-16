# Explicit release requirements and provisional designs

Implemented development slice (2026-11-16), behind existing product_knowledge and story_analysis gates. No execution or ingestion feature is enabled.

## Review and generation

Story pages offer explicit current knowledge, approved release-change context, or approved provisional story-only context. Selection never starts a model call. Members can record intentional change, correct-story or needs-clarification decisions. Project ADMIN explicitly approves immutable contexts; unresolved decisions cannot approve an intentional change. Reasons, expected behavior, release, story snapshot, analysis identity and approver are retained. Requirements contexts are approval manifests, not another product knowledge store.

Knowledge snapshots and approvals remain unchanged. Release successors inherit prior approved release changes automatically. Corrections target rule identities. Removal requires an explicit absence expectation. Generation projects the final release expectations instead of conflicting original acceptance criteria; authors must include retained behavior that the release should cover. The original story remains stored unchanged. Unaffected independently sourced knowledge remains available; same-story extracted proposals cannot validate themselves. Human-approved changes are labelled as requirements authority, not independent evidence.

Provisional contexts require explicit reviewed story-only analysis and human context approval. Meaningful descriptions may supply provisional requirement excerpts when acceptance criteria are absent. Scenarios/cases retain provisional labels, release, context ID/digest and criteria basis, and still require their existing design reviews. They never claim product-knowledge validation or silently fall back from trusted generation.

## Activation and history

Explicit activation is per story and named release, not a global replacement of current product knowledge. Atomic unique activation receipts select one winner per parent; repeated approval retains the original authenticated approver. Activation conservatively flags affected catalog designs for review by base knowledge version or rule references. Prior approved versions and execution records are untouched. Per-release review markers accumulate.

Impact reconciliation is idempotent. An interrupted activation remains pending and blocks release-context use until an explicit retry completes its captured impact list. No browser run, execution replay or model retry is involved. Stale story/knowledge/analysis inputs require a new reviewed context. Generation pins the selected context through scenarios, cases and design approvals.

## Compatibility and limits

New requirement_contexts collection with a project/story/type/date listing index; unique Mongo _id supplies receipt exclusivity. No existing-data migration or startup backfill. Deploy API and UI together; retain the prior knowledge-writer cutover prerequisite. Legacy calls without a context retain existing generation safeguards. Context approval requires project ADMIN independently of optional test-design admin-review policy.

Bounded to 40 decisions per draft, 100 retained effective changes, 250 KB per context, 50 listed contexts, 100 activation-chain links and 1000 catalog records per type for impact inspection. Larger datasets require follow-up pagination/maintenance. Release impact marking is deliberately conservative. These requirements manifests do not authorize automation execution.

The canonical account AI-allowance preflight correction is included: versioned account subscriptions no longer hit the obsolete combined 3-request preflight; selected Managed/BYOK limits remain enforced by the existing gateway reservation. No balances are reset.

## Verification

Isolated backend fixtures: 12 requirement-context tests and 10 story-analysis mode tests passed. Earlier slice regression runs: 65 knowledge, 10 test-design review, 4 scenario-count and 13 separate-allowance tests passed. Source TypeScript and scoped ESLint passed. Browser checks use a real local browser with intercepted authentication/API fixtures, not live Mongo or AI. Four browser checks passed: release approval/activation/selection, provisional no-criteria generation, clarification recovery and existing analysis/scenario controls.

No live Mongo concurrency, real provider generation, production deployment or customer execution qualification is claimed. Production knowledge history and databases were not modified.
