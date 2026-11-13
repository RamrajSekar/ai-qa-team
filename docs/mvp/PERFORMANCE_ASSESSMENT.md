# Navigation performance — 2026-11-13

Priority: resolve slow login/workspace navigation before further product features.
Assessment baseline: `dev`, `e3519d095364fa3c603df59b5ed4ce1450b371e6`.
The changes described below are local and have not been deployed or measured in production.

## Observations and confidence

| Finding | Evidence | Interpretation |
| --- | --- | --- |
| First sampled API request was slow | Public production `/features`: 10,301 ms, immediately repeated: 117 ms; both JSON 200, 851 bytes, MISS | A startup/first-request contributor is demonstrated. These two samples do not prove a cold-start cause or establish percentiles. |
| Public pages were substantially faster | Production `/`: 397/104 ms, 37,077 bytes, PRERENDER/HIT; `/pricing`: 148/134 ms, 11,953 bytes, PRERENDER/HIT | Whole-response timings from this Windows host, not browser rendering, TTFB, LCP or signed-in navigation. Pricing content/title were independently validated. |
| Local first-route compilation is slow | Isolated Next development server recorded Stories 49 s (48 s compilation), Scenarios 24.4 s (24.1 s compilation), story detail 62 s (62 s compilation); later Test Cases requests included 62–93 ms total | Development compilation is a demonstrated local contributor. It does not explain Vercel production rendering. Host load and filesystem costs have not been isolated. |
| Refresh requests multiplied during parallel page reads | Executable utility regression reproduced four refreshes for four concurrent 401 reads before the fix | Shared client behavior affects all pages using `apiFetch`. It does not prove expired sessions explain every reported slow navigation. |
| Test-case specifications waited for optional result metadata | `ProjectTestCatalog.load` awaited `loadSummaries` before clearing the entire table's loading state | A stalled metadata response hid an otherwise available table. Held-response UI regression now verifies early rendering. |

Measurements used confirmed production aliases `https://ai-qa-team.vercel.app` and
`https://ai-qa-team-api.vercel.app`, two sequential GETs per path, without login,
model/provider calls or database writes. Initial probes against deployment-specific
URLs returned protection content and are excluded entirely from application timings.
The Vercel connector subsequently accessed the protected deployment successfully:
landing HTML 200/HIT and actual `/features` JSON 200/no-store.

Vercel's latest production records at inspection were UI commit `309368ba19b44b2bca3feeae92f3a244b2041fea`
from `dev`, and API commit `e3519d095364fa3c603df59b5ed4ce1450b371e6` from `main`.
Review why UI production follows `dev` before relying on main-only releases; no
project settings were changed. The recent sanitized Redis log check found a successful
connection and no fallback/timeout in that bounded result, so Redis is not established
as the cause. Aggregate runtime-log counts provide no request durations. The metric
query was rejected (400); no production P50/P95 or cold-start counts are claimed.

## Fixes in this slice

- Shared API client sends JSON Content-Type only for string request bodies, avoiding
  the unnecessary preflight trigger on ordinary cross-origin GETs. Other custom
  headers can still require preflights. Preserve explicit headers/Headers instances,
  multipart boundaries, cookies and response normalization.
- Concurrent expired-session requests share an in-flight refresh. Authentication
  endpoints do not trigger redundant refresh; failed refresh can be attempted by a
  later request; each original request retains its single retry limit. The shared
  refresh has a bounded 10-second timeout, independent of browser execution budgets.
  A caller's cancellation releases that caller immediately and prevents replay,
  without cancelling other callers' shared refresh. No private response cache.
- Testcase data renders before result/approval metadata. Pending status says Loading;
  unavailable metadata does not enable execution selection or invent an approval.
- An app-layout loading boundary gives page-transition feedback across workspace
  routes. It does not accelerate the backend or bypass feature/authorization gates.
- Fixed-label API startup timings measure `mongo_indexes`, `mongo_probe` and
  `redis_probe`, recording duration/outcome only. Original startup order and failures
  remain intact; no indexes, migrations, connectivity safeguards or timeouts were removed.

Relevant sources: `ai-qa-team-ui/src/utils/api.ts`,
`src/components/projects/ProjectTestCatalog.tsx`, `src/app/(app)/loading.tsx`,
`ai-qa-team-api/app/main.py`, `app/utils/startup_timing.py`.

## Verification

From `ai-qa-team-ui`:

```powershell
node --test tests/api-navigation-performance.test.cjs tests/api-proxy.test.cjs
.\node_modules\.bin\eslint.cmd src/utils/api.ts src/components/projects/ProjectTestCatalog.tsx 'src/app/(app)/loading.tsx'
.\node_modules\.bin\tsc.cmd --noEmit --incremental false
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
# Existing separate UI regression installation, not the execution runner.
$env:PLAYWRIGHT_MODULE_PATH='C:\Users\ram\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
node --test --test-concurrency=1 tests/design-review-pages.test.cjs tests/manual-test-execution.test.cjs tests/test-design-approval-ux.test.cjs
```

The UI server is an isolated source copy, with `NEXT_PUBLIC_API_URL=http://feature-api.test`,
running `next dev --webpack --hostname 127.0.0.1 --port 3123`. Tests intercept all API/auth
calls and use synthetic cookies; they do not establish real-login production performance.
Eight client behavior checks plus two proxy checks passed. The three browser files
passed 16 checks, including five project-page transitions, shared-request counts,
held result metadata, manual results, approval and execution hiding.
The first focused rerun after pending-status wording changes failed because that edit
introduced an invalid source encoding; the server reported a compile error. The file
was restored to valid UTF-8 and the focused checks were rerun. Preserve this failure
as an editing/regression finding, not a backend or navigation latency sample.

From `ai-qa-team-api`:

```powershell
..\.feature-flags.venv\Scripts\python.exe -m unittest discover -s tests -p test_startup_timing.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_feature_flags.py -v
```

Three timing tests passed with doubles, including secret-canary exclusion and failure
propagation. Focused lint and TypeScript passed. Run `git diff --check` from the
repository root. Final focused-browser/feature-history results are recorded below.

Final current-source results: 23 feature/history compatibility tests passed with
doubles; the two focused navigation/held-metadata browser checks passed after the
encoding correction. The eight client and two proxy checks passed again. No claim
is made that the earlier failing rerun passed. Current checks do not qualify
signed-in production speed or demonstrate reduced API startup latency.
The final redundant combined lint/type invocation was interrupted after producing
no static-check completion output; the preceding lint/type invocation passed.
Do not count that interrupted repeat as an additional pass.

## Remaining priority / next bounded work

1. Deploy only through the normal reviewed release process, then capture startup
   stage durations and correlate them with request timing. Imports, Mongo TLS/index
   round trips and host provisioning remain hypotheses, not proven individual causes.
   Avoid removing startup indexes or changing Redis behavior without that evidence.
2. With the user's normal authorized login, time Dashboard, Account, AI Configuration,
   Overview, Stories, Scenarios, Test Cases and Environments on first and warm visits.
   Save only sanitized route/status/timing summaries, never cookies, passwords or raw HAR.
   This signed-in production journey is NOT RUN in this task; no account credentials
   were supplied or sessions forged. Also verify expired-session restoration.
3. Compare a clean isolated Turbopack dev run against the current Webpack run before
   changing the default development command. For a production-like local comparison,
   use an isolated copy/config with `npm run build`, then `npm run start -- --port 3124`;
   do not run a production build in the same output directory as an active dev server.
4. Optimize identified backend/query stages with measured before/after evidence.
   Overview currently waits for project, stories, testcases and environments together;
   assess separate panel loading and bounded projections before introducing caches.
   Account settings also joins multiple responses. No cross-user/project response cache
   should be introduced to hide latency.

No production configuration changes, migrations, load testing, browser-provider runs,
AI calls or new product features were performed. Production performance remains open.
