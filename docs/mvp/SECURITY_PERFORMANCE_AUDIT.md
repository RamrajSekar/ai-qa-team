# Test Design security/performance audit — 2026-11-20

This is a scoped code/dependency audit and isolated regression exercise, not a
penetration test or production performance certification. No production database
writes, real provider generation, migration, execution or feature activation occur.
Existing uncommitted Jira work is excluded from the delivery.

## Confirmed code findings and fixes

| Finding | Evidence and remediation |
| --- | --- |
| High: refresh/access token confusion | `app/utils/jwt_handler.py` previously checked signature/expiry only. Access decoding now requires access purpose, expiry and a string email; refresh decoding explicitly requires refresh purpose. Tests reject swapped cookies on the auth dependency, profile and refresh paths. Existing issued typed tokens remain valid; untyped legacy tokens require sign-in. |
| Password/Redis work blocked unrelated requests | `app/routes/auth_routes.py` invoked synchronous bcrypt and session Redis I/O inside async endpoints. These operations now use Starlette's bounded thread pool. Held-operation regressions prove the event loop progresses while the work is pending. The Redis transport also gains a 10-second read timeout alongside the existing connect timeout. This is not a total request deadline or a measured production speedup. |
| Malformed local login and OAuth-only password login failed as server errors | Explicit bounded field checks return sanitized 422 errors; absent/invalid stored password hashes return generic 401. Missing local signup passwords fail before database access. OAuth user creation still permits no local password. |
| Repeated/unbounded authorization lookups | `app/utils/account_references.py` validates at most 1,000 input test-case references before resource database work, deduplicates IDs and resolves multi-case references in one query. Every referenced project still requires authorization, including foreign-project references. This guardrail does not raise modern execution limits or permit larger runs. |
| Missing tabs after feature-loading failure | `FeatureFlagsProvider.tsx` and `Sidebar.tsx` now distinguish loading/failure from disabled configuration and offer explicit Retry settings. A settings failure never enables a feature or displays the legacy project Team fallback. No settings cache or automatic metered work is added. |

## Local feature reconciliation

Only boolean feature assignments were inspected/edited in the ignored backend
`.env`; no credentials are included in this report or committed. Duplicate feature
keys were consolidated using the previous last-assignment values. Document upload
and Jira import flags changed from true to false pending their qualification.
Restart the local API for new environment values to take effect. Hosted configuration
was not changed; these local edits do not update Vercel.

| Group | Intended effective settings |
| --- | --- |
| Core Test Design | `customer_accounts`, `account_subscriptions`, `separate_ai_allowances`, `product_knowledge`, `story_analysis`, `story_management`, `scenario_generation`, `test_generation`: true |
| Manual execution | `manual_test_results`: true; automation flags remain false |
| Approval policy | `test_design_admin_review`: false intentionally; explicit authorized member approval remains required |
| Unqualified integrations | `jira_story_import`, `jira_api_token_setup`, `knowledge_uploads`, `knowledge_media_processing`, `knowledge_image_interpretation`, `knowledge_ask`: false |
| Encryption preparation | `KNOWLEDGE_ENCRYPTION_REQUIRED=false`; setting true is fail-closed, not encrypted storage |
| Deferred UI/delivery | `account_invitation_email`, `repository_ui`, `bug_reproduction_ui`, `automation_execution_ui`, `test_execution_ui`, `native_execution`, `visual_runner_lab`, `visual_runner_batches`, `approved_visual_run_admission`, `approved_visual_run_execution`, `approved_workflow_worker`: false |
| Existing optional authoring | `reusable_workflows`: true; this does not authorize worker execution |

Do not enable all defaults wholesale. Repository policy switches with true defaults
are not proof of delivered capabilities. Preserve account isolation and versioned
allowances even if rollout flags are subsequently disabled.

## Verification and limits

- 13 new isolated backend auth/token/reference tests passed.
- Six existing session/cookie tests, 29 customer-account tests and 12 account billing
  tests passed. Seven legacy Google OAuth tests passed with their account-rollout
  flags explicitly disabled; the initial invocation inherited local account mode
  and failed two legacy fixtures before this environment correction.
- 15 frontend tests passed: feature recovery (three hook-harness tests), API retry,
  cancellation, refresh deduplication and proxy regression tests.
- Scoped React ESLint and 15 frontend tests passed after dependency updates.
  Hook tests are not browser end-to-end verification. Original working-tree
  TypeScript after the upgrade encountered incompatible old `.next/dev` generated
  types. A fresh isolated Next 16.4.6 production build (webpack) then passed, including
  TypeScript and static generation, with no private env file and an unreachable local
  backend. The original user cache was preserved.
- Boolean local-setting checks passed: no duplicates, unfinished gates disabled.

## Dependency advisory review

`npm audit --omit=dev --json` initially reported 28 vulnerable production dependency
entries (two critical, 18 high, seven moderate, one low). This is an advisory count,
not proof that each advisory is exploitable through this application.

- Next.js 16.0.6 → 16.4.6; matching eslint-config-next 16.4.6.
- Axios 1.13.2 → 1.21.1; Zod 4.1.12 → 4.6.7.
- Compatible proxy-addr/sharp/postcss/source-map dependency updates were requested;
  the lockfile captures the actually resolved versions. No forced major upgrade.
- `shadcn`/`shadcn-ui` are existing source generators, with no application imports;
  preserve them in devDependencies rather than shipping them as runtime dependencies.
  The shadcn generator remains on major version 3 (3.8.5).
- Final production-only scan: **zero known advisories**. Full scan including build/dev
  tooling: **21 entries (13 high, seven moderate, one low; no critical)** remain.
  These are not fixed merely by changing dependency classification. Treat developer
  generators/build tooling as trusted-input-only until separately upgraded/qualified.
- No arbitrary `npm audit fix --force`, new runtime framework or dependency removal.

## Release work that this audit does not certify

- Live Mongo approval concurrency, quota race safety and tenant isolation across
  all export/job paths still require the Phase 1 qualification exercise.
- Application-layer encrypted knowledge storage, private ingestion infrastructure,
  Jira transactions and Ask provider quality remain separately gated.
- Legacy GitHub repository integration retains provider tokens; this audit does not
  claim those records are encrypted or remove the supported repository flow.
- General edge/login abuse throttling and distributed load qualification remain
  release work. Thread offloading prevents event-loop blocking; it is not unlimited
  capacity or a substitute for abuse controls.
- Backend dependency environments/manifests remain divergent. A reproducible Python
  dependency/advisory review remains open; no speculative mass upgrade was applied.
- Production signed-in timings, P50/P95, cold starts and browser recovery have not
  been measured in this slice. Follow PERFORMANCE_ASSESSMENT.md for measurement limits.
- No database migration is required. Deploy compatible auth callers together;
  retain knowledge approval-receipt cutover requirements independently.
