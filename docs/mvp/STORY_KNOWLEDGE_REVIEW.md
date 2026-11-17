# Simple story-to-knowledge review

Story conflicts now support one explicit combined approval in the existing story workspace. Project members can submit proposed decisions. Project ADMIN is required for approval and activation; account/platform roles alone do not grant project knowledge authority. Delegated Lead permissions and email review notifications remain post-MVP. No email is sent.

## User flow

Compare Current knowledge and Story requirement. Choose Intentional product change, Correct the story, or Needs clarification. An intentional change specifies replacement/removal, explicit expected behavior and reason. Other blocking findings require explanations. Review changes shows the exact before/after delta and affected catalog designs. Admins use Approve story and update knowledge; members use Submit for review and can reopen the saved submission. Ordinary story/analysis approval never publishes knowledge.

After approval changes apply now, or stay approved/pending for a named future release until explicit activation. No scheduler is introduced. The advanced release-generation controls remain available collapsed below the main review.

## Persistence and correctness

Immutable story-change manifests/authorization receipts reuse requirement_contexts. A manifest pins the story snapshot/digest, current knowledge parent/digest, analysis/digest, exact decisions, expected behavior, reasons and captured impact. A submission is not approval. The server-owned authenticated approver identity/name/ADMIN role/time is immutable on retry. Correct-story/clarification submissions cannot approve a knowledge change.

Publication reuses ProductKnowledge.create_version and approve: a deterministic successor preserves every omitted approved rule, targeted corrections retain identity/category and removals require explicit reasons. Existing single-winner knowledge receipts prevent concurrent overwrites. An approval applies to the exact saved story requirements; it does not edit the story text or independently validate its own claims. Source records identify the originating story and reviewed human requirement change. Same-story evidence exclusion remains intact for analysis/generation. No AI call is needed for submission or approval.

The canonical knowledge receipt is the publication boundary. If the response or subsequent catalog impact marking fails, retry the same explicit approval/activation; do not submit a duplicate. A completion receipt records reconciliation. Retries never republish or reactivate historical versions and preserve the original approver. Future activation fails closed when the pinned story, analysis or knowledge changed. Failed competing approvals require a new comparison/review rather than an automatic rebase.

Affected scenario/testcase catalog metadata becomes Needs review. Approved design snapshots and execution histories are untouched. Current analysis may become stale after a knowledge successor; no generation safeguard is bypassed and no browser/model action starts on navigation. Requirements authority is distinct from independent source evidence.

## Limits and compatibility

No existing-data migration or new feature activation. Uses existing product_knowledge/story_analysis gates and existing requirement_contexts listing index. Existing knowledge backend cutover prerequisites still apply. Records are bounded to 40 decisions and 40 other finding answers, 250 KB per review, canonical 100-rule/60000-character knowledge bounds and 1000 catalog records per type. Latest 50 submissions are displayed; larger review-history management is follow-up. Listing shares current-context reads to avoid repeating full knowledge-history traversal for every review; responses omit stored story snapshots.

Tests use isolated synthetic Mongo/auth/AI fixtures and intercepted local browser APIs. Real-provider generation and live database failover qualification remain separate. This change does not enable email, ingestion or execution.

Verification: 86 isolated backend tests passed across combined approval, release contexts, story modes, knowledge correctness, test-design review and training. Seven intercepted-API browser checks passed. TypeScript and scoped ESLint passed. No live Mongo/provider test was run.


## Approval/status presentation refinement — 2026-11-17

Completed combined approvals now expose whether the saved story digest still
matches the current story. The detail UI retains Story change approved and the
reviewer name when the exact story is unchanged, while separately explaining that
the old knowledge comparison requires refresh. Analysis stale flags/generation
checks remain unchanged. A later story edit removes the current-match indication;
the historical approval is not rewritten or revoked. A new current analysis with
unresolved findings still displays Findings need review, not an approved verdict.

Corrected UTF-8 review labels. Scenario generation uses a responsive control row
with concise help and an Open Scenarios link. Detailed scenario management remains
in place for now; migration to the separate Scenarios tab is deferred pending the
user's next decision. Existing manual Add/Edit/Delete flows are preserved.
