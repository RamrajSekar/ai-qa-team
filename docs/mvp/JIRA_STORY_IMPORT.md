# Read-only Jira Cloud story import

Development slice, 2026-11-15. Disabled by default. Production provisioning and live qualification are deployment prerequisites.

## Configuration

Private backend configuration:

```dotenv
FEATURES__JIRA_STORY_IMPORT=false
JIRA_SECRET_MASTER_KEY=
JIRA_OAUTH_CLIENT_ID=
JIRA_OAUTH_CLIENT_SECRET=
JIRA_OAUTH_REDIRECT_URI=
```

Keep the flag false until qualification. The master key must be a separately generated URL-safe base64 32-byte key, stored privately and backed up; it is not a Jira token and must not be set to `false`. Losing/changing it requires reconnecting existing connections. Story management must also be enabled. No credentials belong in frontend environment variables or source control.

## Atlassian sign-in (primary connection)

Register **one platform-owned distributable OAuth 2.0 (3LO) application** in the Atlassian developer console. Customers must not create their own client application. Enable Jira read scopes `read:jira-work` and `read:jira-user`, configure distribution for other users when appropriate, and register the exact frontend callback URL, e.g. `http://localhost:3000/jira/callback` for isolated development or the fixed HTTPS UI origin plus `/jira/callback`. Store its client ID, secret and callback in the private backend variables above. Credentials are configured privately by the operator; keep import disabled until provisioning and qualification are complete.

Stories → Import from Jira → **Connect Jira** redirects an account Owner/Admin with project membership to Atlassian. After consent, the callback strips authorization parameters from the browser URL and offers an explicit Continue step. The server discovers authorized sites; the user selects a site, loads its accessible projects and saves a project selection. Users never enter hostname, Cloud ID or an API token. Optional acceptance-criteria custom-field mapping remains available.

The consent state is random, hashed in MongoDB, bound to the authenticated user/account/project and connection revision, expires in ten minutes and is consumed atomically before code exchange. Uncertain exchanges cannot be replayed; reconnect. A separate encrypted ten-minute grant holds the token during site/project selection. Only discovered site identities and retrieved project keys can be selected. Connection replacement uses revision comparison. Tokens stay encrypted server-side; callback codes and client secrets are never returned in API responses. OAuth records receive TTL indexes. Disconnect wipes local connection credentials; imported stories remain intact. Revoke access separately in Atlassian if needed.

This bounded slice requests **no offline access or refresh token**. Access-token expiry requires explicit reconnect, avoiding unqualified rotating-refresh-token handling. Refresh/long-lived unattended connections are a follow-up requiring serialized refresh ownership, uncertain-response reconciliation and real-provider qualification. Project discovery currently shows the first 50 projects and identifies truncation; further browsing is a follow-up. Local API permissions still apply independently of Jira consent.

[Atlassian's 3LO documentation](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/) governs app registration, consent, accessible resources and scopes. New connections use OAuth only. The legacy API-token setup flag, request model and POST connection endpoint have been removed. Existing encrypted token connections remain readable and can be disconnected or replaced through OAuth. Never use customer API-token collection as public SaaS onboarding.

## Import and re-import

Authorized project members enter at most ten explicit issue keys. Jira content uses trusted GET endpoints, while OAuth code exchange uses the fixed Atlassian token endpoint. Content endpoints include identity, server information, project discovery and [issue details](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/). No arbitrary URL/JQL, redirects, attachments, AI generation, Jira write-back or background synchronization is supported.

Preview maps summary, description and optionally acceptance criteria. Missing criteria remain empty. Bounded ADF text extraction omits unsupported embedded content with a warning. Users review fields before applying. Re-import compares the last imported baseline with local edits and the new snapshot; conflicting replacements require explicit selection. Unselected local fields remain unchanged. Changes after preview reject the apply. Existing analysis content digests enforce stale-context handling; imports never approve knowledge or designs or alter execution history.

Deterministic account/project/cloud/issue identity prevents duplicate creation. Apply atomically saves stories, usage, sequence and a reconciliation receipt using a MongoDB transaction. New stories require an active migrated account subscription with story allowance. New stories remain pending. Public story numbering retains the existing sequence; account-local numbering is outside this task.

Previews expire after ten minutes through a TTL index. An uncertain apply must be reconciled by explicitly retrying the same preview; there is no automatic replay. An expired preview requires a new reviewed snapshot. A completed receipt is short-lived too; the durable deterministic story identity still prevents duplicates.

## Release prerequisites and verification limits

- Keep disabled until an isolated replica-set/Atlas database verifies real transactions, simultaneous imports, rollback, counter/quota behavior and TTL cleanup. Current transaction tests use rollback-capable doubles, not a real MongoDB server.
- Verify real OAuth app distribution, callback/session behavior, consent/revocation, scope permissions, custom fields, ADF content, rate limiting and site/cloud matching. None has been tested against live Jira.
- Existing story CRUD now uses project membership rather than creator-only visibility so teammates can access imported stories. Account/project authorization remains mandatory.
- No data migration or real service call was performed. Startup adds a preview TTL index through the existing index initializer. Deploy all code before enabling the flag.
- No execution, model, media ingestion or existing Jira-trigger capability is enabled.

Focused automated coverage is in `test_jira_story_import.py`, `test_feature_flags.py` and `jira-import.test.cjs`. Record actual results in the delivery report; these checks do not establish live-provider readiness.

## OAuth verification — 2026-11-16

- OAuth/backend suite: 16 passed (includes the nine import regressions); feature-policy suite: 24 passed.
- Browser checks: three passed with intercepted API/auth: disabled entry, reviewed import, and consent callback/site/project selection with no exchange on mount or refresh.
- Source-only TypeScript and changed-component lint passed. The standard TypeScript command encountered malformed pre-existing `.next/dev/types` artifacts; the separate source check excludes those generated files and does not establish a fresh production build.
- Git whitespace check passed. No live Atlassian, real-Mongo transaction, deployment, or production configuration verification was performed. Keep Jira import disabled pending qualification.


## OAuth-only delivery and token-setup removal (2026-11-24)

This PR includes the previously uncommitted Jira OAuth/import integration. New
connections are OAuth-only: the API-token feature flag, credential request model,
POST /connection handler and configure service are absent. The obsolete assignment
was removed from the private local .env without printing other values; that file
is not committed. Remove the obsolete Vercel setting after deployment if present.
Existing encrypted token records remain readable/disconnectable; replacement uses
explicit OAuth consent. No connection or imported-story migration is performed.
The Jira import flag remains default off. No production configuration was changed.

Current verification: production UI build/TypeScript passed. 27 Jira backend checks
and six focused feature-policy/project-story checks passed with isolated doubles.
13 browser checks passed with intercepted APIs (three Jira plus ten catalog/story
regressions). Scoped lint excludes the existing set-state-in-effect findings.

The full 24-test feature-policy suite has 21 passes and three existing quota-fixture
failures: test_free_basic_generation_uses_existing_tier_allowance,
test_manual_catalog_draft_checks_scope_and_quota, and
test_story_scenario_provider_authentication_failure_is_actionable. All three were
reproduced using the unmodified committed HEAD test file at 9915c6d; they fail on
legacy MagicMock transaction/session behavior, independently of Jira changes.
Runtime quota logic was not changed to satisfy those fixtures.

Live Atlassian consent/distribution/revocation, real Mongo transaction concurrency,
rollback and quota/TTL qualification remain prerequisites before enabling import.
No live Jira, model, production data or deployment qualification occurred.
