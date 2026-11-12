# Account AI allowances and experimental pricing

Accepted 2026-11-12. This amendment supersedes the earlier unapproved 25/500
recommendation in ACCOUNT_UI_REFINEMENTS.md. It does not qualify execution,
recording ingestion, enterprise security or payment processing.

## Delivered policy

Accounts with `ai_allowance_version=1` have independent monthly pools:

| Plan | Included AI Credits (Managed) | AI Request Allowance (BYOK) |
| --- | ---: | ---: |
| Free | 25 | 25 |
| Pro | 500 | 500 |
| Enterprise | 5000 | 5000 |

These are configurable starting defaults, not measured cost guarantees. Managed
operations use the existing operation credit cost; BYOK consumes one request per
metered operation. Credits are not tokens, generated-item counts or fixed dollar
amounts. Provider tokens are recorded separately when available. Execution AI is
not included in this policy. Human review does not itself consume a credit.

The backend-resolved provider mode chooses the pool. Switching modes does not
reset usage or trigger fallback. Conditional Mongo reservations prevent concurrent
overspending. Eligible authentication failures refund the reserved pool; ambiguous
timeouts can consume the reservation. Both pools reset together for the UTC monthly
period, with stale requests unable to move the period backwards. Legacy aggregate
usage remains for compatibility; it is not a third quota for migrated accounts.

`FEATURES__SEPARATE_AI_ALLOWANCES` defaults false. Enable alongside account billing
only after reviewing existing-account migration. Once an account is versioned,
disabling the flag does not undo its policy or isolation. New versioned account
subscriptions use server-owned defaults. Normal login/startup does not migrate data.

Configuration: `AI_ALLOWANCES__FREE_MANAGED`, `AI_ALLOWANCES__FREE_BYOK`,
`AI_ALLOWANCES__PRO_MANAGED`, `AI_ALLOWANCES__PRO_BYOK`,
`AI_ALLOWANCES__ENTERPRISE_MANAGED`, `AI_ALLOWANCES__ENTERPRISE_BYOK`.
Existing saved limits require an explicitly reviewed policy change; changing a
default is not permission to reset balances.

## Public pricing

The landing page links to `/pricing`. `GET /auth/pricing` serves the public,
secret-free catalogue from backend configuration. Starting hypotheses are roughly
$499/month Managed, $349/month BYOK and $1000 for a fixed-scope pilot, controlled
by `PRICING__MANAGED_MONTHLY_USD`, `PRICING__BYOK_MONTHLY_USD` and
`PRICING__PILOT_FIXED_USD`. No checkout or automatic paid upgrade is implemented.

The current Pro account model has both pools. These public options are commercial
hypotheses, not separate paid SKU entitlements. Before charging customers, define
SKU-to-mode entitlement mapping, enforce it server-side, and validate token/cost
budgets and invoicing. BYOK customers pay their AI provider separately. BYOK is
optional; enterprises must approve key handling under their own security policy.
Dedicated scoped keys, rotation/revocation and audit controls need qualification;
this page does not establish enterprise readiness.

## Existing-data migration

Stop backend/workers and back up the account subscription documents privately.
From `ai-qa-team-api`, using explicitly configured development services:

```powershell
$env:PYTHONPATH='.'
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_ai_allowances.py
# Review counts, unknown attribution and errors; use the exact returned digest.
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_ai_allowances.py --apply --expected-digest <reviewed-digest> --maintenance-confirmed
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_ai_allowances.py
```

The tool rejects unresolved active reservations and stale subscription snapshots.
Known history is assigned by mode. Unattributed historical usage is conservatively
held against both pools and explained in the UI; this does not assert that both
providers were called. Existing plan and legacy counters are preserved. Repeat
planning after successful application is empty. Multi-account application is not
a transaction: reconcile any partial failure before resuming writers.

One existing development account was backed up, migrated and read back this session:
one unattributed legacy unit produced 1/25 in each pool, with old plan/counters
unchanged. Repeat planning was empty. This was an explicit development operation,
not an automatic or production migration. Execution UI and SMTP flags remain off.

## Verification and remaining gates

Focused allowance regression: 10 tests passed. Real development Mongo/Redis checks
passed three groups for shared-account contention, independent BYOK accounting and
conditional migration/idempotence, with disposable collections and a simulated
provider; no external model calls occurred. Three intercepted browser tests passed
for separate usage meters, anonymous pricing/mobile layout and manual error retry.
They do not establish real-login/provider/payment integration. Historical legacy
regression results remain historical unless explicitly rerun.

Before commercial release, qualify actual provider failures/usage, dollar budgets,
paid entitlements and enterprise credential controls. Private recording storage and
the execution release gates remain unchanged.
