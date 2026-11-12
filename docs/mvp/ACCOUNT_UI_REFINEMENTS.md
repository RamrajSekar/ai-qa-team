# Account UI refinements and optional invitation email

2026-11-12; follows ACCOUNT_TEAM_BILLING.md. Incremental changes on dev, not automatically committed/pushed or deployed.

## Current behavior

- Account ID stays an internal identifier and is not displayed in Account details.
- Workspace order is Dashboard, Account, AI Configuration, Projects. Existing feature/role visibility rules remain.
- Subscription & Usage displays title-case labels. Test Cases is one usage group, with Basic, Medium and Advanced beneath it; tier usage is not duplicated as top-level entries.
- Additional Team Members means account users other than the designated owner plus pending/claimed invitations, not Project Admin assignments. The Free plan now permits two additional members (owner plus two), regardless of project assignment count. Other plan limits/prices are unchanged. This updates the Free account team policy; historical one-user evaluation scope must not be presented as the current account-plan seat limit.
- Approved visual run is removed from Project Overview and preserved on `/projects/{projectId}/test-execution`. The new `test_execution_ui` Pydantic flag defaults false and gates navigation and page mounting. Existing backend authorization/admission/execution gates remain independent; UI hiding does not disable those APIs or delete runs. The execution panel does not load when the new page flag is off.

The local private backend `.env` has these explicit settings (no other environment values were displayed):

```dotenv
FEATURES__TEST_EXECUTION_UI=false
FEATURES__ACCOUNT_INVITATION_EMAIL=false
```

Restart the backend to refresh `/features`; reload the UI. No environment secrets are committed. The new execution page additionally requires test_generation and approved_visual_run_admission; starting a browser still requires its existing separate execution gate. Existing execution remains development-only with its controlled-sample boundaries.

## Invitations now and later

Manual private invitation links remain the default, as requested because no email service is available. The UI creates a one-time link for authorized account administrators and exposes no stored token in invitation lists. Existing API callers remain compatible; POST `/account/invitations` now accepts `delivery: LINK | EMAIL`, default LINK.

Optional email components are implemented using Python standard-library SMTP, with no new dependency. When the feature is enabled, the UI switches to Send Invitation and the API validates server-owned configuration before creating an invitation/reserving a seat. EMAIL responses omit the raw token. The recipient receives the same seven-day email-bound signup link; normal verification, approval and account isolation still apply.

Configure these privately when a provider is ready:

```dotenv
FEATURES__ACCOUNT_INVITATION_EMAIL=true
SMTP_HOST=<provider SMTP hostname>
SMTP_PORT=587
SMTP_USERNAME=<provider username>
SMTP_PASSWORD=<provider password or application password>
SMTP_FROM_EMAIL=<verified sender address>
FRONTEND_URL=<application web URL>
```

Port 465 uses implicit verified TLS; other ports require STARTTLS with certificate/hostname checks. No plaintext fallback or automatic resend/provider fallback. Production links require HTTPS. SMTP credentials are SecretStr-backed and never sent to browsers, run records or logs. Sender/configuration and mail content are backend controlled; account admins select only the invited identity and role.

A successful SMTP submission is recorded SENT (submission accepted, not proof of inbox delivery). A transport error/timeout retains the pending invitation and reserved seat, records UNKNOWN, and returns a sanitized error. It may have been accepted remotely: review/revoke explicitly before reissuing, never blind-resend. The UI refreshes pending invitations after a failed attempt. There is no durable mail queue, bounce tracking or automatic delivery reconciliation. Real provider/inbox delivery is NOT verified and no real email was sent in this task. Configure and verify a synthetic invitation before enabling for customers.

## Existing Free account allowance

`update_free_member_allowance.py` is a default dry-run development helper. It changes only migrated Free accounts whose stored team_members_limit is exactly 1; paid accounts and other custom limit values are retained; a custom Free limit of exactly 1 is indistinguishable from the old default and must be reviewed in the dry run. Review the digest before `--apply --expected-digest <digest>`. Conditional writes stop if the plan/limit changes; usage is never replaced.

For the user's explicitly authorized development Free account, a private BSON backup was taken in the existing restricted Git-ignored backup directory. The reviewed one-field update from 1 to 2 was applied. A direct comparison verified unchanged usage and plan and no remaining update for that account. Legacy user subscription snapshots remain historical. This is not a production migration or payment change.

## Verification

Commands use the existing prepared API environment and isolated Next UI copy documented in ACCOUNT_TEAM_BILLING.md. No BrowserStack or model calls are needed. SMTP tests use transport doubles and assert TLS, role/config gating, omitted response token and no retry after ambiguous failure. New browser checks cover hidden account ID, sidebar order, grouped/title-case usage, current manual links, future email-mode UI, moved approved-run controls and disabled execution-page effects. Actual results are recorded below after completion.


### Current verification results

- Focused backend suites passed: optional invitation SMTP/allowance 6; account billing 12; ownership/migration 27; feature policy 23; legacy project membership 10 (78 tests). Feature flags were explicitly isolated. No mail-provider network calls were made.
- Browser tests with intercepted API/auth: first combined run 9/10 passed. The execution test's first navigation exceeded the existing 90-second budget during isolated Next startup/compilation. After startup completed, that single test passed in about 11 seconds without changing timeouts. The other nine passed: eight account tests (including optional email UI) and story/scenario/test generation navigation. Thus all ten scenarios passed across those attempts; the first cold-start failure remains part of the evidence. This does not establish production rendering performance or browser-execution reliability.
- Execution regression covers approval/preview/admission/start/cancel through intercepted APIs on the new page, disabling admission, disabling the new UI flag without data requests, and absence of the panel on Overview. No real browser-provider session was started.
- The development Free account update was backed up, applied and read back: limit=2, identical plan and usage counters, and no pending repeat update. This is the only existing-account data change in this slice.
- TypeScript passed before the final type-only Overview correction. Focused lint identified four pre-existing `any` types in Overview, replaced with typed agent identities, ReactNode and generic Section props. Final static rerun is recorded below.
- `git diff --check` passed; both requested flags were appended as false to the private ignored backend environment file, without reading/printing other values.

Runtime SMTP delivery/inbox receipt and normal-browser real-account verification remain NOT RUN. Configure provider settings and explicitly enable the email flag before a controlled delivery check. There was no push, deployment or commit in this refinement task.

Final static rerun: TypeScript and focused ESLint on the account settings, sidebar, feature provider, Overview and new Test Execution page passed after the type-only corrections. Final whitespace check passed. The isolated test server was stopped; normal user services were not stopped by this task.
