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


## Simplified generation selection — 2026-11-17

The story page places Requirements for generation beside Generate scenarios, with
Story requirements and Story + approved knowledge. Release authoring is optional,
not the normal route. Story requirements uses a deliberate two-stage review and
approval, then the existing immutable provisional context; it never calls AI or
approves knowledge. A current reviewed analysis (including a reviewed knowledge
comparison) can support this explicit restricted generation approval. This is a
new server-owned approval basis, not a change to legacy provisional context API
requirements. Unreviewed/stale analyses and member approvals remain blocked.
Generated scenarios/cases retain story-only basis and their own design reviews;
knowledge-aware generation and self-source exclusion are unchanged. Selection,
mount and refresh cannot approve or generate. Existing approved contexts can be
explicitly reselected without repeating an approval.

Story review completion shows the immutable reviewer name. New reviews persist
it from authentication; legacy names are resolved for display without rewriting
history. A reviewed missing-detail finding can explicitly propose an additional
knowledge rule through the combined review. Such proposals cannot replace/remove
existing rules; conflict changes still require their exact linked rule. This
addition is human-reviewed requirements authority with same-story provenance,
not independent evidence or automatic promotion of a finding.


### Story-only freshness refinement (2026-11-17)

Explicit story-only generation approval may reuse a reviewed comparison when only
product knowledge changed. Creation and resolution verify the exact current story
digest, latest analysis identity, reviewed status and pinned analysis digest. This
exception applies only to the server-owned explicit_reviewed_story_requirements
basis; legacy contexts and knowledge-aware generation keep their freshness gates.
The UI offers explicit approval for an unchanged approved story and retains the
story-only draft label. Selected Story contains the single review link; the catalog
no longer repeats a top-level Review stories action. No migration is needed.


## Approved story generation — 2026-11-17 amendment

Supersedes the normal selector/two-stage generation approval UX above. Scenarios
uses source story, count and one explicit Generate action. approved_story=true is
an opt-in API contract; existing clients/context APIs retain their behavior.
ApprovedStoryContext verifies the current exact story review or the receipt-backed,
activated combined story change. It writes a deterministic immutable design-context
snapshot, not another approval. The original approver remains the authority.
Pending future releases, edited stories, changed analysis identity/content, corrupt
manifests and changed knowledge heads fail closed. Existing scenario approval and
test-case design approval remain required; generation does not approve drafts.

Current independent rules/flows may supply prerequisites and context within story
scope. Same-story rules are excluded. Explicit approved changes are carried as
human authority, never relabeled independent evidence. Story-only analysis does
not acquire knowledge validation. Story-only outputs remain labeled. Scenarios
and cases pin context ID/digest, exact analysis and knowledge identity; testcase
generation resolves the same context rather than choosing a new one. Context is
rechecked after model completion before returning drafts. No automatic model retry.

The Add/Edit testcase editor now exposes optional Preconditions, one per line.
PATCH omission preserves existing conditions; explicit [] clears them. Earlier
approved design versions and execution results are not edited by catalog changes.

No existing-data migration. New snapshots use the existing requirement_contexts
collection and existing unique _id. Deploy API support before the UI; older APIs
cannot resolve these new snapshots. Preserve the M1 knowledge-writer cutover gate.
No execution/media activation, public publishing or confidential-data qualification.


Verification for this amendment: fixture checks cover reviewed/activated authority,
blocked future activation, changed/corrupt/foreign context, exact case inheritance,
member generation through the HTTP route, and omitted/edited/cleared Preconditions.
Browser checks cover one-action admin/member generation without metadata requests,
Preconditions save/reopen, catalog CRUD/pagination, held summary responses and
existing story analysis. Initial synthetic subscription setup and editor label
locators were corrected before rerunning. No live model or Mongo concurrency/load
qualification was performed; real provider output quality remains unverified.
