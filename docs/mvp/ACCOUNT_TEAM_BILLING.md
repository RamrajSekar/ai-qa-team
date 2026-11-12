# Central account team and shared subscription

2026-11-12 development slice on `dev`; extends [customer ownership](CUSTOMER_ACCOUNTS.md). This is an additive change, not a new payment provider or account-local display-ID migration.

## User journey and permissions

Open Workspace → Account → **Team & project access** (`/settings/account/team`). Account OWNER/ADMIN creates and revokes new-user invitation links, selects an account project, and assigns existing ACTIVE account members as Project Admin or Tester using the retained membership services/APIs. The account owner can explicitly assign themselves Project Admin. The project creator still receives Project Admin on creation.

The project sidebar Team link is hidden when `customer_accounts` is enabled. Existing project Team URLs show a link to the central page; old routes/data remain. Account-off legacy UI and project-admin behavior remain supported. Onboarding can still reuse the TeamManager component for optional assignment.

Account administration permits listing same-account project IDs/names and managing memberships. It does NOT grant content, environment-secret, test or artifact access. Those still require explicit project membership. The shared authentication guard has a narrowly matched `/projects/{id}/team[/{membership}]` exception for authoritative account administrators only; all referenced projects must be in their account. Project-only admins and platform roles cannot use account-management powers. Account member lists remain account-scoped. Project roles in this implementation remain the existing ADMIN/TESTER values; no Lead role was introduced.

`GET /account/projects` is admin-only metadata. Existing project Team APIs now require account OWNER/ADMIN for mutations in account mode; merely hiding a screen is not the permission boundary. Account role editing/ownership transfer/account-member removal and automated invitation email delivery remain separate tasks.

## Shared billing contract

A separate default-off Pydantic flag `FEATURES__ACCOUNT_SUBSCRIPTIONS=true` controls adoption for new accounts and requires migrated billing for existing account users. Keep `customer_accounts` enabled. Existing account ownership migration does not perform this billing migration.

After cutover, `customer_accounts.subscription` is canonical, with `billing_version: 1`. All account members share plan/limits/usage through existing subscription service functions. Legacy `users.subscription` snapshots remain unchanged for history. Once an account is migrated, disabling the flag does not fall back to a second user allowance. Missing migration fails closed when the flag is enabled. Normal login/profile refresh never provisions or resets an account subscription.

New customer signup initializes its account subscription from the server-created free subscription when this flag is on. Invite acceptance joins the existing allowance; it does not allocate a separate free plan. `/auth/me`, login and `/auth/check-plan` expose effective shared subscription data; `GET /account/subscription` provides scope/migration status and usage for the Account details page.

Plan changes preserve usage and AI period. The legacy plan-change endpoint cannot let an ordinary account owner/member grant themselves a paid plan: account administration AND platform administration are required until a verified billing integration is assigned. Existing plan definitions/experimental prices are not changed and no payment collection is implemented.

### Metering

- Projects, stories, scenarios and testcases use the account counter via existing mutation hooks. Testcase complexity allowance reads shared tier counters. Deletions clamp account counters at zero. Profile synchronization returns canonical account counters without reconstructing and overwriting concurrent usage.
- AIUsageService reserves atomically in Mongo against the account, across its users/projects. New records retain caller/project attribution and add account_id/billing_scope. Managed and BYOK share allowance behavior; existing error/refund policy is preserved. Legacy scenario generation in migrated account mode now uses AIUsageService and charges one policy credit per provider operation, not per generated scenario. Existing rate/concurrency controls remain per user/project/operation; account credit reservation bounds total spending, but this is not an account-wide concurrency redesign.
- `team_members_used` means **additional account identities excluding the designated owner, plus pending/claimed invitations**. A person assigned to multiple projects consumes one seat. Creating an invitation reserves a seat atomically; acceptance retains it, and successful pending revocation releases it. Expired invitations retain capacity until revoked; no automatic expiry worker was added. Project assignment/removal/deletion does not change seat count after cutover.
- No commercial billing is attached to synthetic Visual Lab or development BrowserStack runs. Existing legacy execution counters are routed to the shared account through subscription helpers; execution success/failure allowance policy and duplicate legacy execution accounting still require a separately scoped execution-metering review. Do not advertise exact-once execution billing from this change.

Ordinary resource handlers retain existing preflight-check plus mutation-counter patterns: they are shared at account scope but NOT a transactionally atomic reservation across creation and accounting. Simultaneous non-AI resource creations or process interruption can overshoot/drift counters. AI and invitation seat reservation have atomic counter checks, but cross-document persistence interruptions can retain conservative capacity and require reconciliation. A full durable resource reservation/reconciliation ledger is a follow-up before unrestricted commercial self-service. No blind replay or new background reconciliation was introduced here.

## Billing migration (separate from ownership)

Only explicitly configured development services should be used for local checks. Do not run against production. Take a protected backup and stop API/worker writers before applying. Existing account IDs/project URLs remain unchanged.

From `F:\ai-qa-team\ai-qa-team-api`:

```powershell
$env:PYTHONPATH='.'
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_account_subscriptions.py
```

The default dry run shows account IDs, selected plan, proposed usage, errors and digest without printing user profiles, invitation credentials or connection settings. It selects the designated owner's subscription by default. If paid subscriptions conflict, review an explicit source mapping:

```json
{"subscription_sources":{"ACC_existing_account_id":"<reviewed same-account Mongo user ID>"}}
```

Pass `--mapping <private-file.json>` for both dry-run and apply if needed. Plans/limits are copied from one reviewed source; allowances are not added together. Existing user subscriptions stay intact. Resource counters use the greater of summed legacy counters and actual account-project record counts, avoiding a silent reset but potentially carrying conservative historical overcount. Current/unperioded AI usage is preserved in the current month; previous-period usage remains in legacy history. Seat count is reconstructed from unique identities and pending/claimed invitations. Review all totals; exceeding current limits does not delete data or silently upgrade the plan. Active/unresolved STARTED AI reservations block this migration until reconciled.

After reviewing a conflict-free plan, with backup and stopped writers:

```powershell
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_account_subscriptions.py `
  --apply --expected-digest "<new reviewed digest>" --maintenance-confirmed
# Add --mapping <private-file.json> if used for the dry run.
```

Rerun the dry run; expect `account_count: 0`. Apply uses conditional updates including prior owner/status/subscription state. Multiple accounts are not one database transaction: stop on partial failure, inspect and re-plan; never blindly replay. The digest includes source snapshots and proposed counts so changed data invalidates review. Then enable both backend flags, restart and verify Owner/Member subscription values, Team assignments and foreign-access rejection.

Existing-account billing migration is never applied automatically by API startup. After implementation, the user explicitly authorized one development billing migration and confirmed writers were stopped; see the evidence below. Prior ownership migration alone is not billing cutover.

## Verification

Current results are appended after checks finish. Historical ownership checks are in CUSTOMER_ACCOUNTS.md. Real-service fixtures use disposable prefixed collections and synthetic identities, actual development Mongo/Redis/JWT/password authentication and ASGI route handlers. AI provider is a double with zero external calls. Browser UI checks intercept APIs/auth and are separate evidence, not normal-browser-to-real-API qualification.

Commands from the API directory:

```powershell
$env:PYTHONPATH='.'
# Neutralize private developer flags for legacy fixture suites; new tests explicitly enable their own flags.
$env:FEATURES__CUSTOMER_ACCOUNTS='false'
$env:FEATURES__ACCOUNT_SUBSCRIPTIONS='false'
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_account_billing.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 tests/verify_account_billing_real.py
```

UI regression prerequisites: isolated Next dev copy with NEXT_PUBLIC_API_URL=http://feature-api.test on port 3123, installed Playwright/Edge; then from the UI directory:

```powershell
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
$env:PLAYWRIGHT_MODULE_PATH='<installed Playwright module directory>'
node --test tests/customer-accounts.test.cjs
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
```

No account display numbering, navigation performance work, recording ingestion, execution architecture, deployment, commit or push is part of this slice.

### Current-checkout evidence (2026-11-12)

- Backend synthetic suites: account billing 12; customer ownership/migration 27; legacy project membership 10; feature policy 23; AI usage 13; sessions 6; Google OAuth 7; environment secrets 8; product knowledge 8; platform prompts 13. All passed (127 tests across ten suites). Legacy suites run with both account flags explicitly disabled; account tests enable their own flags. Initial legacy membership failures came from inheriting enabled developer flags, then passed with isolated settings.
- Real development MongoDB/Redis with ASGI and synthetic provider: six groups passed: normal password login/account subscription, invitation seats/shared profile, central assignment and foreign-account denial, actual shared-credit Mongo contention, actual seat contention/revocation, and conditional billing migration on disposable records. Fixtures/Redis keys were cleaned up; external provider calls: zero. Earlier attempts exposed missing shared subscription exposure in `/auth/me` (fixed) and an incomplete synthetic project fixture (fixed); they are not claimed as passes.
- Browser-intercepted UI first run: 5/6 passed, with project-selector accessible label failure. After adding the explicit label, the targeted assignment/navigation test passed. Final rerun results are recorded below. These are intercepted APIs/auth, not normal-browser-to-real-API qualification.
- TypeScript/focused UI lint final results are recorded below. Existing datetime.utcnow deprecation warnings remain.
- Normal external OAuth, normal logged-in browser against the actual account, paid billing/provider calls, distributed failure recovery and arbitrary simultaneous resource-create enforcement were not qualified by these checks.

### Explicitly authorized one-time development migration

The user requested existing billing migration and confirmed backend/workers were stopped. A protected local Git-ignored BSON backup of the account and its legacy user subscription was created, read back and SHA-256 verified. The reviewed plan had no conflicts and retained Free with one project, story, scenario, basic testcase and current AI generation used, zero executions and additional members. Apply changed one development account. A repeat dry run returned zero accounts/errors; direct service verification confirmed billing_version=1, ACCOUNT scope and unchanged legacy user subscription snapshots. Private backup and verification receipt remain under `tmp/account-billing-backup-*`; no credentials or customer names are copied into this document. No production service was accessed. The developer can restart the API/UI and verify Account → Team and Account details. The account stays canonical because its migration marker is persisted; enable the billing flag for future new accounts after review.

Final static checks: TypeScript and focused ESLint on the seven changed account/team/navigation files passed. `git diff --check` passed.

Final UI rerun: all 6 intercepted account UI tests passed (about 136 seconds, including local development rendering). The earlier 5/6 failure and targeted correction remain recorded above. This establishes account naming, invitation/revocation, member restrictions, fragment signup, centralized project assignment/hidden project Team navigation and shared subscription display under intercepted APIs. It does not establish normal-browser real-service qualification or improve the separately open local navigation-performance issue.
