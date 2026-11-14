# Teach Your QA Agent — Milestone 1

Implemented locally on `dev`, 2026-11-14. This milestone changes backend knowledge
correctness only. The QA Agent rename, Teach/Review/Save interface, persisted
extractions/reviews and story-only analysis belong to later milestones and are
not delivered here. Document, image and media ingestion gates remain unchanged.

## Incremental contract

The existing POST `/projects/{project}/knowledge/versions` accepts additions or
reviewed corrections in `claims`. The server loads the approved parent and retains
every claim omitted from the submission. Clients never need to copy the parent. Historical snapshots are available through
project-authorized GET `/projects/{project}/knowledge/versions/{version_id}`, even
when older than the overview's latest 100 rows.

- A new claim ID adds a rule.
- An existing ID targets a correction. Changed existing claims must explicitly
  name `parent_version_id`, identifying the version reviewed by the author.
- `removed_claim_ids` explicitly targets removals. The parent must be supplied;
  unknown, duplicate or simultaneously submitted/removal IDs are rejected.
- Omitting a proposal leaves the existing rule untouched. There is no implicit
  deletion by omission or automatic approval of an extracted proposal.
- Answers merge with previous clarification answers. Overwriting an existing
  answer also requires an explicit parent; omitted answers survive.
- Stale explicit parents return 409. Nothing is automatically rebased and approved.
- The full resulting snapshot is validated for citations, project scope, the
  100-claim/30-answer limits and the 60,000-character reviewed-data bound. Oversize
  submissions reject; the server never truncates approved knowledge.
- Drafts contain an immutable `changes` list with add/replace/remove, claim ID,
  before and after values, plus parent, complete claims, answers and digest.
  The existing explicit project-admin approval publishes the entire reviewed
  draft, including any listed removals. Creating a removal draft alone changes
  nothing. Explicitly approving removal of all rules is supported.

No text similarity, AI inference or new rule ID silently replaces another rule.
Whether a new rule semantically contradicts an old one remains a human review
responsibility; this milestone provides identity-based changes, not contradiction AI.

## Atomic approval and storage compatibility

Existing sources, versions, collection and API boundaries are retained. New drafts
use `knowledge_contract_version=2`. They are immutable content snapshots. Approval
is an append-only **receipt in the same `product_knowledge_versions` collection**:

- Receipt `_id` is a deterministic namespace/hash of project plus approved parent.
  Mongo's built-in unique `_id` constraint allows exactly one successor per parent,
  including the empty/root parent. No process-local lock or transaction is required.
- A receipt contains the version ID/digest and authenticated approver/time. It does
  not copy/store another knowledge corpus. It uses `scope_project_id` and a distinct
  `record_type`; ordinary project-version listings cannot expose it as a version.
- Active knowledge follows the accepted receipt chain from the unchanged legacy
  approved baseline. New approvals do not depend on timestamps or a mutable latest
  flag. A competing approval receives 409 and must be reviewed against the winner.
- There is no second write required to complete approval. A lost acknowledgement
  can be resolved by reading the saved version/overview or explicitly retrying the
  same approval. The original approver/time remains unchanged. No model call occurs.
- Physical v2 snapshot rows retain `status=draft`; the receipt is authoritative.
  `ProductKnowledge.record`, `active` and `overview` derive the public approved
  status and approver metadata. New consumers must use this service boundary rather
  than querying `status=approved` directly. Legacy approved rows remain unchanged.
- Retrying a historical approval never reactivates it. Legacy approved history is
  readable; legacy unsaved/destructive draft semantics cannot be approved through
  the new path. Resave a safe successor against current knowledge first.

Deployment requires draining/replacing old knowledge writers together: an older
backend does not understand receipts. No automatic migration/backfill is run.
Previously lost rules or legacy approval forks cannot be reconstructed automatically;
they require explicit historical review. Database rollback, retention/deletion and
administrative recovery must preserve source/version/receipt relationships.

The current reader bounds traversal to 2,048 successors and fails closed beyond
that. Long-history query performance and an explicit checkpoint/compaction protocol
remain follow-ups; never silently delete or squash approval history. Production
durability depends on the configured Mongo deployment/write concern; these tests
do not establish failover or multi-region guarantees.

## Verification

From `ai-qa-team-api`:

```powershell
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_product_knowledge.py -v
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_test_design_review.py -v
```

- Knowledge suite: 18 passed. Covers preservation, rejected/omitted proposals,
  answer retention, targeted correction, explicit removal, immutable history,
  forced competing reads, conflict rejection, lost acknowledgement recovery,
  legacy compatibility, bounds, citation integrity, project/approval guards and
  existing knowledge-aware generation/self-validation/staleness regressions.
- Test-design suite: 10 passed. Its initial run failed because the existing fixture
  omitted the source provenance required by the already-existing self-validation
  protection. The fixture now supplies an independent project source; production
  safeguards were not weakened. An intermediate citation-validation ordering
  regression was fixed before the successful final knowledge run.

Opt-in real development Mongo, synthetic collections only:

```powershell
..\.feature-flags.venv\Scripts\python.exe scripts/verify_knowledge_m1.py --configured-service-is-development
```

The harness requires development/local/test configuration and uses two randomly
named collections, never existing application collections. It performs no API
startup, authentication session creation, AI or browser calls. Majority writes are
requested. Cleanup targets only those generated collection names.

The first separate-database harness attempt returned `OperationFailure`; it was
not counted as a pass. The scoped-collection run passed: two competing approvals,
one winner/one 409, inherited-rule preservation, fresh-service read, historical
read and project isolation. The final expanded run also passed targeted correction and explicit removal. All
temporary test collections were deleted.

No frontend changes are part of M1. Current UI/browser, real-login authorization,
provider calls, production deployment, fault-injected Mongo failover and load tests
were not run. Prior UI/provider results are historical evidence only.

## Milestone 2 handoff — await user review

Ready to build QA Agent navigation on the same knowledge route and a Teach/Review/
Save UI against this additive contract. Show retained rules and the saved change
list, pin explicit parents for edits/removals, and handle 409 by reloading for human
review. Keep pending proposals/rejections/clarifications durable, source-key AI
results recoverable and uncertain extraction calls explicit-retry only. None of
that persistence or automatic extraction has been implemented by M1.

Story-only analysis/provisional generation assessment is M3. No execution, agent
entity/framework, vector store, upload activation, deployment, commit or push is
included in this milestone.


## Subsequent compatibility audit — 2026-11-14

See [writer inventory, old-client tests, reproduced mixed-backend hazard and
cutover requirements](KNOWLEDGE_APPROVAL_COMPATIBILITY.md). The audit reran 25
knowledge, 10 test-design and 8 ingestion fixture checks plus real development
Mongo contention. M2 development can use one upgraded backend; mixed old/new
writers on the same database remain a rollout blocker. No M2 work began.
