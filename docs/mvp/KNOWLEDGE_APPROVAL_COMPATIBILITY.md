# Knowledge approval compatibility audit

2026-11-14, `dev` working tree based on
`8047917b348f847c1e3330cbaff81b6f4c59045b`, including uncommitted Milestone 1.
This is a local repository/service audit, not an inventory of deployed processes.
No Milestone 2 implementation or application behavior changes were made by this audit.

## Receipt: meaning and rationale

A receipt is an immutable approval event, stored beside snapshots in the existing
`product_knowledge_versions` collection. Its fields are:

- deterministic `_id = "knowledge_approval:" + hash(project, parent_version_id)`;
- `record_type=knowledge_approval`, `scope_project_id`, parent and approved version ID;
- approved snapshot digest, authenticated approver and approval timestamp.

It stores approval metadata, not another knowledge copy or agent entity. Mongo's
unique `_id` elects one successor per project/parent, including the root. Different
versions racing from the same parent cannot both publish receipts. Repeating the
same approval returns the original approval; it never reactivates an old version.

This replaces the old read-current/check-parent/update-one-draft sequence: two
requests could check the same parent and then independently mark two drafts
approved. The new approval linearizes at one insert. A lost acknowledgement is
recoverable without a second mutable status write or repeating extraction/AI.

See `app/services/product_knowledge.py:37` (key), `:42` (public approval view),
`:55` (active chain), `:181` (approval), and `:201` (insert). Physical v2 snapshots
stay `status=draft`; read methods derive their public approved status from the
receipt. Existing legacy approved rows remain unchanged.

## Complete writer inventory in current checkout

Paths below are relative to `ai-qa-team-api`, except the UI row. Searches covered
application code, scripts and the isolated document processor, plus the UI callers.

| Path | Writes | Receipt compatibility |
| --- | --- | --- |
| `app/routes/product_knowledge_routes.py:121` → `ProductKnowledge.add_source` at `app/services/product_knowledge.py:83` | Manual text/pasted transcript source; insert only | Cannot approve/version knowledge |
| Routes `:127` → service `:119` | Metered extraction returns unapproved proposals; no version insert | Cannot approve; durable extraction recovery remains M2 |
| Routes `:115` → service `:286` | Story-origin source, then extraction; provenance is server-owned | Cannot approve; self-validation guard retained |
| Routes `:133` → service `:133` | Immutable v2 successor snapshot with complete merged content and explicit changes | All API draft creation uses this path |
| Routes `:146` → service `:181` | Single-winner receipt | Only project-knowledge approval writer found; project ADMIN required |
| `app/workers/knowledge_ingestion_worker.py:91`, `:132` | Derived document/image-observation sources through `add_source` | No version/receipt writes or auto-approval; ingestion remains disabled |
| `app/services/knowledge_ingestion.py:93`, `:129`, `:142` | Intake/status/cancel/retention job records; deletes originals | Does not mutate sources, snapshots or approvals |
| Service `:218`, `:251` and routes `:152`, `:164` | Analysis documents and reviewed resolutions in `story_analyses` | Analysis review does not approve or rewrite knowledge |
| UI `ai-qa-team-ui/src/app/(app)/projects/[projectId]/knowledge/page.tsx:61`, `:72`, `:95`, `:104` | Calls source/extract/draft/approve APIs; local proposal edits otherwise | No database access or alternate approval path |
| `scripts/verify_knowledge_m1.py:53` onward | Calls the same service against generated synthetic collection names | Test-only; cleanup targets those names only |

No source update/delete API, mutable version update API, alternate knowledge
approval route or second application writer of `product_knowledge_versions` was
found. Editing corrections/answers creates successors. Test fixtures directly seed
legacy documents but are not deployed writers. The decoder outputs files/JSON and
does not connect to Mongo. Repository migration scripts do not approve knowledge.

The router is registered once at `app/main.py:141`. The router's product-knowledge
feature dependency and private-response policy are at routes `:27`; membership is
checked for sources/drafts/reads, ADMIN for approval. Platform roles are not an
alternate knowledge approval path.

Current readers also use the service: knowledge-aware scenario/test design
(`knowledge_test_design.py:25`, `:38`), test-design approval context
(`test_design_review.py:57`), and existing specification context
(`visual_specifications.py:116`, `:130`). They do not directly choose v2 knowledge
by stored `status=approved`. No execution code was changed in this audit.

## Compatibility findings

### Updated backend with old clients: safe, with explicit UX differences

The existing URLs still route to the new service. Old draft payloads with only
title/claims/parent/answers remain accepted. Omitted old rules are retained. A stale
parent returns 409. Corrections/removals require an explicit current parent.
Server-owned status/contract marker/digest/change log/approver fields cannot be
injected into a draft (`KnowledgeDraft`, `models/product_knowledge.py:59`;
strict extra-field rejection in `models/approved_visual_run.py:14`). There is no
PATCH/PUT version endpoint. Approval ignores caller-supplied approver metadata and
uses authenticated identity. Every approval, regardless of caller age, uses receipts.

The existing UI's text at knowledge page `:79` still says to include every retained
claim, and its `:90` Remove claim action only omits a local proposal. Under the new
contract omission cannot delete an approved rule. This is a **UX incompatibility,
not an authorization/concurrency bypass**. Smallest fix in M2: explain automatic
retention; label local proposal discard accurately; send explicit removal IDs only
after a clear human removal review, and show the saved change log before approval.

### Legacy data: readable; unsafe drafts deliberately fail closed

- Legacy approved snapshots remain readable/current until superseded; approved
  content, source evidence, approver/time and history are not rewritten.
- A legacy approved version retried through the new API returns unchanged; it does
  not reactivate history.
- An unapproved legacy draft receives 409 on approval. Resave reviewed changes as
  a successor of the current approved version; never bulk-mark these drafts approved.
- No receipt backfill, new collection or new unique index is required. `_id` is
  already unique. Verify there is no externally managed collection validator that
  rejects the new receipt shape before deployment; that was not inspected here.
- Multiple historically approved legacy forks retain the old timestamp-selected
  baseline. The new mechanism does not repair previously lost rules/forks.

### Old backend writing to the same database: HIGH risk, reproduced

`git show HEAD:ai-qa-team-api/app/services/product_knowledge.py` still contains the
pre-M1 writer: it finds the latest stored approved row and mutates a draft's status
without a receipt. A still-running server from that revision can ignore receipt
approvals, create/approve a different legacy baseline, or directly mark a v2 row
approved. The new process cannot force that old binary to obey its protocol.

The characterization test at `tests/test_product_knowledge.py:411` injects an
old-style approved row after receipt approval and demonstrates that the reader
selects that legacy baseline, disconnecting the active receipt chain. **Its pass
confirms the hazard; it is not evidence that mixed-version deployment is safe.**
Arbitrary privileged Mongo writes are likewise outside HTTP protections.

All writers in the **current working tree** are compatible. All **deployed** writers
cannot be declared compatible: deployments, old preview URLs, scheduled scripts,
running API processes and their database credentials were not inspected.

## Smallest safe remedy and deployment sequence

No application rewrite or receipt backfill is recommended for a controlled cutover.

1. Inventory every local/API/preview/production instance that can reach the target
   database. Prefer separate databases/credentials for previews and production.
2. Back up source/version collections. Pause knowledge writes; disable the feature
   and drain in-flight requests on **all old instances**, not just the new one.
3. Retire/block old deployment URLs and stop old processes. Remove their DB access
   where needed. Updating environment variables for a new deployment does not prove
   old deployments lost their existing configuration/credentials.
4. Deploy/restart the receipt-aware backend as the only knowledge writer. Confirm
   build identity and project-authorized read/history/draft/approval behavior.
5. With synthetic data, verify preservation, competing approvals and repeat reads;
   then re-enable knowledge writes. Never roll back to the old writer against a
   receipt-bearing database; prefer a forward fix or remain read-only.
6. Enable/use M2 only against this upgraded boundary. No ingestion gates change.

If coexistence cannot be ruled out, the rollout stays blocked. A follow-up can
freeze an explicitly reviewed legacy baseline and reject unexpected raw approvals
on new readers. That is defense-in-depth only: new-code guards do not stop an old
server with write credentials. Strong database enforcement would require separately
scoped validation/permission migration and mixed-writer tests, not a casual flag.

## Risk assessment

| Risk | Severity | Disposition |
| --- | --- | --- |
| Old backend/preview retains DB writes | High | Reproduced; controlled cutover/isolation required before shared rollout |
| Direct queries interpret v2 physical draft status | Medium | No current app bypass reader found; future consumers must use service; old readers are incompatible |
| Old UI promises implicit deletion/full-copy editing | Medium | Data remains safe; correct labels/removal review in M2 |
| Legacy unapproved drafts cannot publish directly | Medium | Intentional 409; resave reviewed successor, preserve original |
| Legacy forks or previously omitted rules | Medium | No automatic reconstruction; historical/manual audit if present |
| Growing receipt-chain read cost/2,048-successor ceiling | Medium | Existing documented bound; separate checkpoint/performance qualification |
| Mongo failover/backup restores/unknown validators | Unverified | Not established by development contention check |

## Current audit verification

Commands from `ai-qa-team-api`:

```powershell
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_product_knowledge.py -v
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_test_design_review.py -v
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_knowledge_ingestion.py -v
..\.feature-flags.venv\Scripts\python.exe scripts/verify_knowledge_m1.py --configured-service-is-development
```

| Check | Environment | Result |
| --- | --- | --- |
| Knowledge compatibility/correctness suite | ASGI/auth/Mongo/provider doubles | 25 passed, including seven new audit tests |
| Different drafts approving simultaneously | Forced same-parent/root reads; ASGI doubles | One 200, one 409 |
| Same draft approving simultaneously | Three ASGI calls with forced same-parent reads | Three 200s, one receipt, same original approver/time |
| Repeated historical approval | ASGI/service doubles | No extra receipt, no reactivation |
| Legacy records and malicious old payloads | ASGI/doubles | Approved history preserved; unsafe draft 409; forged draft fields 422; version mutation methods 405 |
| Old-backend hazard | Direct synthetic old-style write | Hazard reproduced (not remediated by new API) |
| Test-design compatibility | ASGI/database/auth doubles | 10 passed |
| Disabled ingestion/source-only worker | Worker/API/parser/AI doubles and temp files | 8 passed; no real upload/provider/worker execution |
| Real development Mongo | Random synthetic collections, majority writes | 2 competing approvals: 1 winner/1 conflict; preservation, fresh service recovery, history, correction, removal and project isolation passed |
| Test Mongo cleanup | Real development Mongo | Generated collections deleted; existing application collections not accessed; zero AI calls |
| Whitespace | `git diff --check` | Passed |

No frontend/real-login/provider/deployment tests ran. No credentials, raw database
errors, document content or personal paths were printed. No production inspection,
database migration, runtime behavior change, feature activation, commit or push.

## Milestone 2 verdict

**Not a blocker to M2 implementation against one receipt-aware backend.** It is a
**blocker to mixed-backend/shared-database deployment or activation** until the old
writer inventory and cutover are verified. M2 should include the small UI contract
adjustments above. User review is still required before starting M2.


## M2 writer amendment — 2026-11-14

The additive training coordinator now writes `knowledge_training_reviews`, creates
sources through ProductKnowledge, and saves drafts through its existing version
creator with a server-owned idempotent draft identity. It cannot approve knowledge;
all approvals still use the receipt endpoint. New source reads remain scoped.
See QA_AGENT_TRAINING_M2.md for review revision CAS, extraction recovery and tests.
The old-backend cutover requirement is unchanged; no rollout was performed.
