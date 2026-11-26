# Phase 2: versioned account entitlements

2026-11-26. Implementation prepared for review. No production account was migrated,
no live environment settings were changed and no paid purchase/activation was enabled.
See [pricing rollout](PRICING_ROLLOUT_PLAN.md) for the remaining phases.

## Policy and compatibility

- Canonical models accept `team` and `business` in addition to `free`, `pro` and
  `enterprise`. Pro remains Pro with its saved limits; it is never renamed Team.
- New Team/Business defaults use the same validated `PRICING__TEAM__...` and
  `PRICING__BUSINESS__...` capacity settings as the offer catalogue. Price changes
  are display-only. Capacity changes become effective only through an explicit
  policy snapshot, never a page load, login, deployment or provider-mode change.
- A reviewed account snapshot has `subscription.entitlement_version=2`, retains
  `ai_allowance_version=1`, and uses `testcase_complexity_policy=SHARED_TOTAL`.
  The total test-case limit is shared across Basic, Medium and Advanced, rather
  than three additive pools. A configured zero remains zero.
- Five included users means four additional identities beyond the owner. Pending
  invitations still reserve capacity; project assignments do not allocate seats.
- Migration preserves every usage counter, AI period, migration attribution,
  subscription status/dates/provider, execution allowance and legacy user snapshot.
  Existing knowledge/test approvals and execution histories are untouched.
- Downgrades never delete data or refill AI balances. Active accounts retain reads,
  edits, deletes and human review of saved records when over capacity. New creation
  for an exhausted resource is blocked; independent resources remain available.
  Existing AI reservation policy blocks the exhausted mode's AI requests. Account
  and project authorization, current-context and immutable approval checks remain.

## Enforcement and delivery boundary

V2 project/story creation atomically writes the record and counter on the account;
project creation includes its creator membership in the same transaction. Scenarios
and test cases retain the existing transactional reservation/persistence mechanism.
Jira imports retain their transactional story counter. AI and invitation reservations
also match the saved limit, preventing a stale pre-downgrade read from granting
capacity against the old cap. These operations are account-scoped, not per user.

Pre-adoption project/story writers preserve their legacy behavior, including their
known separate preflight/counter race. The strengthened creation path applies only
after reviewed v2 adoption. Deploy all new writers together and stop old writers
before cutover. Mongo must support transactions; v2 creation fails closed without
them. A lost acknowledgement must be reconciled against saved records, not blindly
replayed. Sequence numbers may have gaps after failed creation.

The default-off legacy repository importer cannot run for a v2 account: its direct
writes lack qualified capacity admission. Existing legacy behavior stays behind its
flag. This does not remove the static scanners, parser, history or repository data.

There is no public Team/Business activation endpoint. The retained plan-change API
requires platform administration (and account administration in account mode),
rejects new paid activation, and cannot overwrite a v2 policy. Legacy user plan
changes now preserve usage/dates instead of replacing the whole subscription.
Billing stays disabled and the public paid offers remain planned.

## Explicit development migration

This helper supports explicitly configured development/local/test services only.
It is not a production cutover tool or an instruction to migrate live customers.
Back up the selected account documents privately, stop API/worker writers and
reconcile active/uncertain AI work and open resource reservations first.

Create a private mapping containing only reviewed account selections, for example:

```json
{"ACC_fixture":"team"}
```

`free`, `team` and `business` are explicit targets. Existing Pro/Enterprise accounts
are skipped unless explicitly selected for one of those targets. Custom Enterprise
contracts remain outside this migration. Account billing and separate AI migration
must already be complete; no missing counters are invented.

From `ai-qa-team-api`, with `PYTHONPATH=.` and explicit development connection settings:

```powershell
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_account_entitlements.py --mapping <private-mapping.json>
# Review account IDs, old/new plan, limits, over-capacity values, errors and digest.
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_account_entitlements.py --mapping <private-mapping.json> --apply --expected-digest <reviewed-digest> --maintenance-confirmed
```

The dry run compares saved counters with actual account-project inventory and
unique account identities/pending invitations. Under-counts block adoption and
require separate reviewed reconciliation; conservative higher counts are retained.
Apply rechecks inventory and active work inside each account transaction, compares
the complete reviewed subscription/owner/status/pending snapshot, and inserts an
immutable `account_entitlement_receipts` record with before/after policies and time.
Changed counters/configuration invalidate review. Receipts have no TTL and retries
cannot reset usage or overwrite a later policy. Rerunning the dry run after success
has no changes. Different accounts are separate transactions: a partial failure
requires inspection and a fresh plan, not a blanket replay. No startup migration
or new background task is introduced.

## Verification

Current checks, with disposable fixtures only:

- 95 backend checks: account entitlements 12, billing 12, customer accounts 32,
  Jira import 10, separate AI pools 13, Free complexities 8, quota contracts 4,
  public pricing 4. Legacy allowance checks used their expected Managed setting
  of 25 in the test process; no environment file was edited.
- 13 real local Mongo policy/fault/concurrency checks, including five writers
  competing for one project/story slot, membership rollback, shared Business
  complexity capacity, stale AI/seat caps, inventory drift and receipt idempotence.
- 13 existing real local quota checks and 25 authenticated local journey checks
  after explicit Free v2 adoption. Journey model responses are deterministic
  doubles; no external AI/Jira/payment request or browser execution occurred.
- 15 intercepted-API browser checks across usage display, Dashboard, pricing and
  account navigation; desktop/mobile account display inspected. Production UI
  build/TypeScript, scoped ESLint and `git diff --check` passed.

Reproduce local Mongo checks only against the separate loopback replica set
`qaTestDesign` on port 27129, never the application database:

```powershell
..\.feature-flags.venv\Scripts\python.exe scripts/verify_account_entitlements.py --confirm-isolated-local --output ../tmp/pricing-phase2-real.json
..\.feature-flags.venv\Scripts\python.exe scripts/verify_resource_quota.py --confirm-isolated-local --output ../tmp/pricing-phase2-quota.json
..\.feature-flags.venv\Scripts\python.exe scripts/verify_test_design_qualification.py --confirm-isolated-local --entitlements-v2 --output ../tmp/pricing-phase2-journey.json
```

Each verifier creates and drops its own database. These checks do not qualify
production failover, payment processing, commercial AI spend or Enterprise service
commitments. Production adoption needs a separately reviewed operational cutover.

## Remaining pricing delivery

| Phase | Next changes | Gate before activation |
| --- | --- | --- |
| 3 — Plan and usage experience | Included/extra seats, separate AI balances, period/reset visibility, persistent 80%/100% notices, clear over-capacity states | Read-only UI and notification deduplication; no purchase grants |
| 4 — Spend safeguards and checkout | Managed spend reservations/reconciliation, account/platform budgets, measured price validation, verified/idempotent payment events, renewals/cancellation/failure/refunds/tax/proration | Review commercial terms/provider, real failure-path qualification and explicit launch decision |
| 5 — Extra users and AI packs | Confirmed seat purchases, separate durable Managed/BYOK pack balances, receipt identity, consume included capacity first | Define expiry/refunds and qualify duplicate events, concurrent consumption and rollover without resetting purchased units |
| 6 — Execution and Enterprise | Measure execution costs and choose separate units; define supported custom capacity/support | Qualified execution/security/reliability and contractual commitments; no implied SSO/SLA features |

Phases 3/4 now have a gated development implementation; see
[usage and guarded billing](PRICING_USAGE_BILLING.md) for current qualification
and remaining launch gates. Ordinary Test Design paid pricing is complete only
after Phases 4/5 and launch qualification; Phase 6 is conditional future expansion.
