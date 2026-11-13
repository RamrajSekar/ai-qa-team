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


## Subscription presentation and AI credit meaning (2026-11-12)

The account section now uses a dedicated responsive SubscriptionUsage component: bold title-case Plan/Status, a monthly AI Credits card, Workspace Capacity with one Test Cases total and nested complexity meters, Team Capacity and Execution Usage. Existing light/dark workspace tokens are reused. Progress indicators are named for accessibility; unlimited, unavailable, zero and exceeded limits have explicit text. No allowances, counters or backend contracts are changed by this presentation update.

The old AI Generations label referred to `ai_gen_used`/`ai_gen_limit`, a shared account monthly AI allowance. AIUsagePolicy currently includes KNOWLEDGE_EXTRACTION, STORY_ANALYSIS, SCENARIO_DESIGN, TEST_DESIGN and BUG_INTERPRETER. ProductKnowledge, KnowledgeTestDesign, migrated legacy scenario generation and BugInterpreter call AIUsageService for these tasks. Most policy operations cost one credit per request (bug interpretation is configurable), not one credit per generated item; timeout/provider-unavailable attempts can consume credits. Human review does not spend an AI credit by itself. Legacy non-knowledge testcase conversion may use no AI request and is not marketed as AI test design.

Execution AI has no AIOperation entry and is not part of this credit counter. The development visual-button provider call is separate (visual-runner/linux/visual_button_probe.py); future execution AI must be routed through explicit scoped metering/budgets before commercial use. Executions has its own existing counter, with qualification limits recorded in ACCOUNT_TEAM_BILLING.md.

Current configured allowances remain Free=3, Pro=50, Enterprise=None (unlimited). A basic AI knowledge → story analysis → scenario design → test design journey takes approximately four requests, so Free=3 cannot cover that full path without an allowance adjustment. Suggested starting hypotheses are Free=25 and Pro=500, with a configurable Enterprise cap and separate bounded execution allowances; these are recommendations only, not accepted or implemented plan changes. Measure token/cost distributions and define retry/failure and period policies before final commercial packaging.

Code evidence: ai-qa-team-api/app/app_config/plan_limits.py, app/services/ai/ai_usage_policy.py, app/services/ai/ai_usage_service.py, app/services/product_knowledge.py, app/services/knowledge_test_design.py and app/services/ai/scenario_generator.py. No live AI calls, quota migration or payment change is authorized by this UI review.

Subscription redesign checks: four focused intercepted browser tests passed (plan/status bold weight, AI scope copy, capacity grouping, hidden IDs/sidebar, narrow-screen overflow and unlimited quota semantics). After visual review, a compact three-card workspace row and full-width testcase group were added; the focused layout/bold/mobile scenario passed again. Desktop screenshot was visually inspected. TypeScript and focused ESLint passed for the new component and AccountSettings integration; whitespace check passed. No live model/provider calls, database updates or plan allowance changes were made by this redesign. Suggested 25/500 allowances remain unapproved hypotheses.


## Onboarding and allowance clarity — 2026-11-13

AI Setup is an optional fifth step, after the existing optional import; Ready is
now step six. It reuses AIConfigurationManager from Workspace → AI Configuration
and its project-authorized backend routes. Managed is preselected for unconfigured
projects and is already the gateway default. No customer key is required for
Managed. Existing saved BYOK remains selected; never silently switch it. Testing or
activating a provider remains an explicit action and can contact the provider.
Skip/Continue only save onboarding progress, not provider settings. A previous
in-progress step-five user now sees the optional AI step before Ready; completed
users are not reopened or migrated. No account/credential data migration is needed.

Provider settings remain project-scoped despite their workspace entry point. The
creator receives an ADMIN membership. Account OWNER/ADMIN can manage same-account
assignments centrally under Account → Team; account ownership does not grant
project content access. Existing last-active-admin guards reject sequential
removal/demotion; those checks currently count then write, so cross-request races
still need a dedicated atomicity follow-up. Do not claim distributed guarantees.

Versioned subscription meters are labelled Managed AI Requests and BYOK AI Requests.
Persisted field names, entitlements, usage and billing do not change. Zero limits
show Not included; missing limits show Unavailable; null remains Unlimited. Basic,
Medium and Advanced remain grouped under Test Cases. The free plan explicitly sets
medium/advanced limits to zero in app/app_config/plan_limits.py; no paid upgrade or
allowance change is introduced. The historical migration explanation remains in
AI_ALLOWANCES_PRICING.md, while the normal UI shows one concise explanation.

Verification results for this slice are recorded after running the focused checks;
intercepted UI and database doubles are not real provider/login verification.


Verification (2026-11-13): eight focused intercepted account/onboarding/usage checks
passed, followed by two provider-onboarding checks passing after fixing dropdown
assertions and adding the explicit Provider accessible label. The earlier UI attempt
started before the cold server was ready and was interrupted; subsequent failed
provider assertions are not counted as passes. Final Managed-default, explicit
BYOK test/activation, skipped setup and existing-BYOK preservation are covered by
synthetic intercepted fixtures, not real provider calls. Ten project membership,
12 account billing and 13 AI configuration tests passed with doubles. Legacy
membership tests initially inherited account-enabled local configuration and failed;
the fixture now explicitly disables account flags for its legacy scenario. A new
Managed-default test initially used an invalid request fixture; it was corrected to
the actual LLMRequest contract and all 13 configuration checks passed. No application
role or billing behavior was changed to make these tests pass. TypeScript and the
initial focused lint passed; final expanded lint and whitespace results follow.

Commands: from ai-qa-team-ui, use the isolated Next server and external Playwright
setup documented in PERFORMANCE_ASSESSMENT.md, then run
`node --test --test-concurrency=1 --test-name-pattern="onboarding|zero complexity|missing complexity|split AI|subscription redesign|account details hides" tests/customer-accounts.test.cjs`.
From ai-qa-team-api run the existing development Python environment with
`-m unittest discover -s tests -p test_project_membership.py -v`,
`-m unittest discover -s tests -p test_account_billing.py -v`, and
`-m unittest discover -s tests -p test_ai_configuration.py -v`.
No live login, secret, migration, mail, model request or deployment was performed.


Final expanded focused lint passed. The shared manager disables activation until
saved settings load, preventing an initial Managed selection from overwriting a
saved BYOK configuration. The preservation regression additionally holds that
configuration response and verifies activation remains disabled during the wait.
New setup defaults to Managed; completed customers continue to use Workspace → AI
Configuration and are not automatically sent through onboarding again.

Final current-source validation: the two provider-onboarding checks passed again
with the held-response safeguard; expanded lint and TypeScript passed afterward.
`git diff --check` passed. The isolated UI test server was stopped; normal user
API/UI processes were preserved. Changes remain uncommitted and undeployed.


## Onboarding and capacity corrections — 2026-11-13

- Application/environment setup is optional with explicit Skip for now. Back is
  available after Project; returning to Project reuses the created project rather
  than creating another. Existing account naming updates the account, never creates
  a second account.
- Removed Optional import from the wizard only. Repository/import features and
  existing data remain intact. Retained persisted step numbers: 1 Project, 2
  Application, 3 Team, 5 AI Setup, 6 Ready; old step 4 resumes at AI Setup.
- Completed onboarding no longer reopens because the project list is empty.
  Project deletion clears referencing onboarding context and ends that setup wizard;
  subsequent project creation also preserves completed status. Use Create Project
  from the empty dashboard rather than repeating account onboarding.
- Team Capacity and Dashboard include the owner in the displayed total. Free is
  1/3 for owner only: owner plus two additional identities. Billing counters and
  invitation enforcement still use additional seats; admin/project roles do not
  consume another seat. Undefined/unlimited allowances retain their semantics.
- New account-owned projects receive an additive account-local display_id from
  an atomic Mongo counter. New accounts start PRJ001; legacy labels in the same
  account are reserved. Canonical project_id remains globally unique and remains
  in URLs, authorization and references. Existing projects are not renumbered.
  Counters never reset on deletion; failures may leave gaps. Story/scenario/testcase
  account-local display numbering remains backlog, not delivered here.

Verification commands (from repository root unless noted):

- API directory: `..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_customer_accounts.py -v`
- UI directory: `node --test --test-concurrency=1 --test-name-pattern="setup Back|team capacity includes|completed onboarding stays|onboarding AI Setup" tests/customer-accounts.test.cjs`
  requires isolated Next dev server, FEATURE_UI_URL, NEXT_PUBLIC_API_URL=http://feature-api.test
  and PLAYWRIGHT_MODULE_PATH when Playwright is supplied externally. Browser tests
  intercept authentication/API calls; they do not verify real signup/Mongo.
- UI directory: `node_modules\.bin\tsc.cmd --noEmit --incremental false` and
  focused ESLint for changed components; root `git diff --check`.

No database migration, production access, deployment, commit or push is included.

Current-checkout results: 29 synthetic API/account checks and four intercepted
browser checks passed. TypeScript, focused lint and whitespace checks passed.
Initial restricted-environment checks stalled/failed before useful verification;
reruns outside that restriction passed. A temporary source-encoding error in the
isolated UI copy was corrected before the successful browser rerun. No real
login, Mongo contention, existing-account backfill or production qualification ran.
