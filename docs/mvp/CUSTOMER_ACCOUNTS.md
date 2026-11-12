# Customer accounts — ownership and isolation

Development slice: 2026-11-12, branch `dev`, based on `706629fa1b884776e734cb56d6b80f012cad9334`. Uncommitted implementation; rollout remains default off. This document records the initial customer identity/ownership slice. The subsequent [central team/shared billing amendment](ACCOUNT_TEAM_BILLING.md) supersedes the initial project-Team and user-billing behavior below when its cutover is active. It does not declare the Test Design MVP complete.

## Accepted model

One customer account contains users and projects. Each user belongs to exactly one account. Account OWNER/ADMIN manages the customer name and new-user invitations; OWNER alone can invite another ADMIN. Project ADMIN controls project membership for existing ACTIVE users of that same account. Platform OWNER/ADMIN remains separate and cannot bypass account/project authorization. Account membership alone does not grant access to a project.

New local signup or first verified Google/GitHub OAuth signup creates a stable pending account. The existing onboarding flow starts with **Account & Project**: name this account, then create the first project. Naming never creates a second account. Ordinary login never provisions or repairs an account. Invited users join the inviter's account and skip new-customer onboarding; a project administrator then assigns project access. There is no account switcher or self-service account transfer.

Account IDs are opaque `ACC_` identifiers. Existing global project/story/scenario/testcase numbering is preserved. Per-account display numbering is a separate migration. Subscription ownership, usage counters, plan limits and payment infrastructure retain their existing user/project-owner behavior; they have NOT become account-level billing in this slice.

## Implementation and API

- Default-off Pydantic flag: `FEATURES__CUSTOMER_ACCOUNTS=true` in the private backend configuration, only after the rollout gates below. `/features` supplies UI visibility; APIs enforce permissions independently.
- `app/services/customer_accounts.py`: authoritative persisted assignment, pending provisioning, atomic invitation claims and role checks.
- `GET/PATCH /account`, `GET /account/members`, `GET/POST /account/invitations`, `DELETE /account/invitations/{invitation_id}`. Account/member lists are private/no-store; invitation creation returns its credential once to its authenticated administrator.
- `customer_accounts`: account name, setup/status and owner identity. `users`: additive account_id/account_role/account_state. `projects` and project memberships: additive account_id. `account_invitations`: globally unique normalized invited email, account, role, expiry and hashed token.
- `/settings/account` in Workspace; onboarding Account & Project; Project Team adds existing account members. No invitation email sender is implemented: administrator copies/shares the private link.
- Shared authentication resolves explicit resource references before account-scoped work, in addition to existing project role checks. Project lists/history and AI project access retain account constraints. Stale foreign project membership and platform roles do not override them.

Invitations expire after seven days, bind one normalized email and account, and store only a SHA-256 token digest. The local signup link carries the token in a URL fragment; signup submits it in the request body and removes the fragment after success. Verified Google/GitHub identity can accept the pending invitation for its verified email without a local token. GitHub requires a primary verified email from its email API. Never log invitation bodies, credentials, auth headers or cookies. Revocation only removes PENDING invitations; an accepted/claimed invitation cannot be silently revoked/replayed. Expired invitations require explicit revocation before reissue.

Provisioning uses atomic claim and conditional activation, not a multi-document transaction. An interruption can leave CLAIMED invitations or PROVISIONING users. They cannot authenticate. Administrators must inspect and reconcile the exact partial state; login must not silently assign a new account or replay signup. Owner transfer, account role editing, member removal and email delivery are not implemented here.

## Migration and rollout

No existing-data migration was performed by this task. Only disposable synthetic fixtures were applied and removed.

1. Keep the flag off. Take a protected backup and inventory existing users, projects and memberships. Prepare an explicit private mapping with every user assigned exactly once and exactly one OWNER per account. Do not infer that shared project membership means two customers should merge.
2. Dry-run with the command below. Duplicate/non-normalized emails, missing creators, cross-account memberships, conflicting ownership and reparenting block application. Resolve them deliberately. Unknown legacy pending invitees are quarantined as `LEGACY_REVIEW_REQUIRED`; they never auto-join an account.
3. Review the mapping, errors, counts and digest. Stop API/worker writers for a maintenance window. Apply only the reviewed digest. The tool uses conditional updates and stops on changed records. It is not an all-or-nothing transaction: after a partial stop, reconcile and generate a new dry run. Do not blindly retry or automatically roll back ownership.
4. Repeat the dry run; expect no changes. Enable the flag and restart the API, which creates account lookup indexes and unique normalized-email enforcement. Verify normal login, onboarding, invitation acceptance and foreign access rejection before rollout.

Example private mapping (use actual reviewed user IDs, not emails or passwords). Omit `account_id` to generate it automatically:

```json
{"accounts":[{"name":"Customer One","users":[{"user_id":"<existing Mongo user ID>","role":"OWNER"}]}]}
```

PowerShell from `F:\ai-qa-team\ai-qa-team-api`, using the prepared API environment:

```powershell
$env:PYTHONPATH='.'
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_customer_accounts.py --mapping <private-mapping.json>
# Only after backup, reviewed plan and stopped writers:
..\.feature-flags.venv\Scripts\python.exe scripts/migrate_customer_accounts.py --mapping <private-mapping.json> --apply --expected-digest <reviewed-digest> --maintenance-confirmed
```

Existing approvals/history/data are retained; no IDs are renumbered, subscriptions copied or jobs migrated. With the flag on, unmapped existing users receive an account migration/setup error. Turning the flag off is NOT an ownership rollback: assigned users/projects remain isolated. Restore or reversal requires an explicit reviewed migration, not removing account fields casually.

## Verification and limits

Current-checkout evidence is recorded below; older audits are historical. API service verification uses real configured development MongoDB/Redis, real bcrypt/JWT/cookies and actual route handlers through ASGI, but disposable prefixed collections. It is not a normal browser-to-running-API or external OAuth-provider qualification. All task-owned collections and refresh-token fixtures were cleaned up.

The first real-service attempt failed invitation signup because default BSON datetime decoding returned naive UTC, while expiry comparison used aware UTC. The implementation now normalizes the comparison; a focused naive-BSON regression is included. The next real-service attempt passed signup/name/project, normal login without new account, invitation plus separate project membership, foreign/stale membership denial, actual Mongo invitation contention (one creation, one conflict), persisted reads through another session, and repeatable migration on disposable records.

Focused commands:

```powershell
# API directory; synthetic fixtures
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_customer_accounts.py -v
# Opt-in only with explicitly configured development Mongo/Redis; disposable namespace
$env:PYTHONPATH='.'
..\.feature-flags.venv\Scripts\python.exe -X utf8 tests/verify_customer_accounts_real.py
# UI directory
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
# Isolated Next test copy with NEXT_PUBLIC_API_URL=http://feature-api.test, port 3123
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
$env:PLAYWRIGHT_MODULE_PATH='<installed Playwright module directory>'
node --test tests/customer-accounts.test.cjs
```

UI tests intercept synthetic APIs/auth; they cannot establish real account or OAuth integration. External provider login, full normal-browser real API login, deployment, existing-customer migration, distributed failure recovery and account billing remain separate gates. No model/browser-execution provider calls are needed for this slice.

### Final current-checkout results

| Check | Environment | Result |
|---|---|---|
| Customer accounts | ASGI/provider/database doubles | 22 passed, including BSON UTC expiry and claimed-invitation interruption guards |
| Project membership / Google OAuth / session auth | Synthetic fixtures | 10 / 7 / 6 passed |
| Feature policy / AI usage / platform prompts | Synthetic fixtures | 23 / 13 / 13 passed |
| Environment secrets / product knowledge | Synthetic fixtures | 8 / 8 passed |
| Account onboarding/settings/signup UI | Browser with intercepted APIs/auth | 4 passed |
| Signup, login, invite, project isolation, Mongo contention, persisted reads and migration | Real development Mongo/Redis + actual ASGI route handlers; disposable records | All seven groups passed on two post-fix runs; cleanup confirmed |
| TypeScript / focused changed-file ESLint | Local static checks | Passed |
| Normal browser against real API / external OAuth | Not run | Manual qualification remains |

Total focused backend tests: 110 passed across nine suites. Initial failures were retained and corrected: real invitation expiry timezone mismatch, a synthetic BSON comparator mismatch, and feature-policy expected defaults missing the new flag. Existing datetime.utcnow deprecation warnings remain. Browser UI checks took about 177 seconds including development compilation; this does not establish navigation performance improvement. No dependencies/lockfiles or browser execution runtime changed.

## Automatic migration IDs (2026-11-12)

New signups already generate random account IDs. Migration now permits an omitted `account_id`: it retains the reviewed owner’s assigned account ID, or derives a stable UUID-based ID from that owner’s immutable user ID. This is an identifier, not an authentication secret. The same owner yields the same ID across dry-run/apply, company renaming and membership edits. Explicit IDs remain supported. No mapping file or database is mutated during dry-run. The CLI reports resolved `account_ids` alongside the plan digest. Regenerate and review the digest if changing a previously explicit mapping. One valid explicit OWNER and complete reviewed user assignments remain mandatory; conflicting existing assignments still block migration.

Focused verification after this change: 24 account/migration tests passed, including automatic-ID stability, read-only planning, repeat after apply, existing owner ID preservation and foreign-assignment rejection. `git diff --check` passed. No live database migration or additional real-service verification was performed for this change.

## Recovering projects whose creator was deleted

An account mapping can include `legacy_project_ids`, an explicit reviewed list of existing projects. This is not a claim-all switch. For an unmapped/deleted creator, the planner assigns the account and makes its reviewed OWNER the project's current creator/owner, preserving the original value in `legacy_created_by`. A claim cannot override a project already assigned to another account or a creator mapped to another customer. Unknown/duplicate project claims block apply. Truly missing project records still require separate investigation.

Example property inside one account entry:

```json
"legacy_project_ids": ["PRJ008", "PRJ013", "PRJ014", "PRJ015", "PRJ016", "PRJ017", "PRJ018"]
```

Memberships for identities absent from users are retained as `LEGACY_REVIEW_REQUIRED`, with their original `legacy_status` preserved, including old ACTIVE memberships. They do not silently reactivate if that email signs up again. The normal owner-membership backfill can grant the new project owner access on the next authorized project read. Stories, cases, runs and their historical authors remain unchanged; legacy creator-only child-resource visibility and old billing references may need a separately reviewed follow-up. No history rewrite or deleted-user recreation is implied by project recovery.

After editing the private mapping, rerun dry-run and review its NEW digest and errors. Never use an earlier digest. Back up and stop writers before explicit apply. Current verification: 27 account/migration tests passed, including recovered-owner provenance, membership quarantine, idempotent re-planning, unknown/duplicate/foreign claims and truly missing projects. `git diff --check` passed. No live migration was applied during this change.


Account presentation/Free team amendment (2026-11-12): [ACCOUNT_UI_REFINEMENTS.md](ACCOUNT_UI_REFINEMENTS.md) records hidden account IDs, centralized workspace order, grouped testcase usage, two additional Free account members, optional SMTP delivery (disabled; manual links retained), and the relocated/default-hidden Test Execution page. Other quotas and execution qualification gates remain unchanged.
