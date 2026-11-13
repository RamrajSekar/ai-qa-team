# Test Design UI/UX refresh

2026-11-13 superseding catalog amendment: Scenarios and Test Cases now use tables
with on-demand review; manual result and Release/Cycle execution UI is documented in
[MANUAL_TEST_EXECUTION](MANUAL_TEST_EXECUTION.md). The automated Lab/execution/history
surfaces require the new default-off `automation_execution_ui` presentation flag.
Existing automation controls/history are preserved. The verification below is prior
evidence unless specifically rerun for this slice.

## Project review pages amendment — 2026-11-12

The current refresh extends the shared workspace to Stories (list and detail),
Scenarios, Test Cases, Test Execution and a dedicated Execution history page.
It preserves the existing purple brand and light/dark themes, with no new package,
backend endpoint, data migration, model call or execution-engine change.

- Stories show loaded-record/criteria summaries, local search and a readable table.
  Detail separates acceptance criteria from out-of-scope information and retains
  story analysis and scenario-generation actions. Load/save protection remains in
  the backend. Failed deletion is visible and releases the busy state.
- Scenarios and Test Cases have page-local search/status filters and labelled
  summary counts. Scenario approval remains distinct from case steps/expectations.
  Creation keeps approved-source selection and existing manual/generation routes.
  Protected deletion uses the shared focus-contained confirmation dialog rather
  than a browser confirm. Existing edit/review actions and server ownership rules
  remain in place. Expansion keeps detailed procedures and approved context available.
- Test Execution explains the controlled development boundary, shows available
  cases/environments, provides retry/empty states and links to history. Navigation
  does not start or admit a browser run. Existing feature flags and approval,
  preview, admission, explicit start, cancellation and authorized evidence remain.
  This redesign does not enable the hidden execution feature.
- Sidebar Execution history now opens `/projects/{projectId}/execution-history`.
  The overview history section/anchor remains compatible and links to the new view.
  History is read-only and reuses the existing authorized `/execute` listing; it
  does not reinterpret legacy status as a new business verdict or merge separate
  synthetic/worker stores. API pages contain up to 200 user-visible records before
  local project filtering. An empty project page may therefore have a later page;
  Next is driven by the unfiltered response size. Search/counts describe only loaded
  records, never a complete project total. Server-side project search/pagination is
  future work, not a silently claimed capability.

### Verification for this amendment

Use the isolated UI server and synthetic API URL described below. New command:

```powershell
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
$env:PLAYWRIGHT_MODULE_PATH='C:\path\to\existing\node_modules\playwright'
$env:DESIGN_REVIEW_EVIDENCE='F:\ai-qa-team\tmp\design-review-evidence'
node --test --test-concurrency=1 tests/design-review-pages.test.cjs tests/story-test-generation.test.cjs tests/workspace-appearance.test.cjs
```

Fixtures intercept authentication/API traffic. They exercise search, status filters,
protected deletion failure/cancel, source eligibility, explicit expected-result
display, history retry/project filtering, disabled execution, no automatic start,
story detail, mobile overflow and workspace themes. Screenshots are ignored local
artifacts. These checks do not verify real login, Mongo, AI, BrowserStack execution,
production deployment, large-data performance or broader accessibility compliance.
The earlier verification sections below remain historical.

Amendment results: six new page checks passed on the final rerun; the existing
story/scenario approval flow, two theme/workspace checks and the approved visual
run approve/preview/admit/reload/start/cancel check also passed (10 distinct checks).
The expanded run initially found mobile overflow in Story detail; grid-child
minimum widths were corrected so its scenario table scrolls internally. An earlier
run found a status-field accessible-label issue and an overly broad test selector;
both were corrected before the passing reruns. TypeScript, changed-file ESLint and
`git diff --check` passed. Light/dark desktop and mobile screenshots were inspected.
Execution flags, dependencies, backend routes and persistent data were unchanged.


2026-11-12, `dev`, following merged PR #3 (`f21771a`). This development implementation follows that merged PR. Git history records
its subsequent publication; the verification below does not establish deployment readiness.

## Direction and changed behavior

Preserve the existing application, purple brand and light/dark workspace themes.
Use one readable sans-serif baseline, consistent primary/secondary buttons, clear
page headers, bordered cards, visible focus and explicit disabled/error states.
Shared styling covers the workspace; public landing/auth have their own scoped
appearance. No new UI dependency or component framework was introduced.

- Shared workspace control styles now apply to portal dialogs, not only descendants
  of the sidebar shell. Tailwind scans all source components. Body/theme defaults
  and landing margins are consistent.
- Onboarding has five actual columns for its five saved progress steps, a clear
  project/application/team/optional-import/ready hierarchy and a mobile layout.
  Setup remains account/project onboarding, not product training.
- The existing Radix dialog primitive now backs onboarding, project creation,
  story, scenario and environment forms. Shared wrapper supplies focus containment,
  Escape/focus restoration and viewport bounds; outside clicks do not discard forms.
  Nested environment dialogs remain supported.
- Project creation and setup completion report errors and release busy states.
  Optional repository import respects its UI flag; no backend routes/jobs are disabled.
  The finish screen points users toward product knowledge and stories.
- The standalone onboarding page no longer refreshes `/auth/me` whenever replacing
  the user object. AuthProvider owns initial session loading. Its old effect could
  perpetuate a refresh loop; the synthetic regression bounds the observed request count.
- Stories, scenario/testcase catalogs, knowledge and environments share page hierarchy
  and action spacing. Story tables scroll inside a keyboard-focusable region on narrow
  screens. Environment list errors are visible; raw environment response logging is removed.
- Platform prompt editing shows required template slots, unsaved changes, immutable
  publication status and explicit confirmation. Project admins do not see platform
  management. Authentication copy reflects product knowledge and test design.

This refresh does not claim every legacy modal/flow has been independently redesigned
or qualified. Shared baseline styling reaches them; lower-priority repository, legacy
execution, billing and data tools retain their behavior. No runtime execution feature,
model preview, private media upload or fine-tuning was added.

## Verification environment and commands

Use a separate Next copy with no private `.env` files and an existing `node_modules`
junction. Set `NEXT_PUBLIC_API_URL=http://feature-api.test` only for that isolated
server and run on port 3123:

```powershell
# From the isolated UI copy (never change normal backend settings for these fixtures):
$env:NEXT_PUBLIC_API_URL='http://feature-api.test'
$env:NEXT_TELEMETRY_DISABLED='1'
node node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port 3123
```

From the real `ai-qa-team-ui` directory, in a separate terminal:

```powershell
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
$env:PLAYWRIGHT_MODULE_PATH='C:\path\to\existing\node_modules\playwright'
$env:UI_EVIDENCE_DIR='F:\ai-qa-team\tmp\design-ui-evidence'
$env:WORKSPACE_LIGHT_SCREENSHOT="$env:UI_EVIDENCE_DIR\workspace-light.png"
$env:WORKSPACE_DARK_SCREENSHOT="$env:UI_EVIDENCE_DIR\workspace-dark.png"
$env:WORKSPACE_MOBILE_SCREENSHOT="$env:UI_EVIDENCE_DIR\workspace-mobile.png"
node --test --test-concurrency=1 tests/design-system.test.cjs tests/product-knowledge.test.cjs tests/story-test-generation.test.cjs tests/workspace-appearance.test.cjs
node node_modules/typescript/bin/tsc --noEmit --incremental false
```

Playwright is existing UI regression tooling, not part of the isolated executor.
The fixtures intercept auth/API data. They do not establish normal-login, Mongo,
AI or BrowserStack integration. No actual password or provider call is used.
Screenshots live under ignored `tmp/design-ui-evidence`.

Checks cover desktop/mobile, five-step onboarding, inline failure recovery, nested
environment dialog cancellation, focus containment/restoration, approved prompt
activation, project-admin denial and theme persistence. Visual screenshots were
inspected for onboarding, prompt editor and mobile story/testcase layouts.

Initial new-suite run: 2/4 passed; corrected tests to await focus restoration and
use the actual guard text. Subsequent run: 4/4 passed. Expanded existing/new run:
7/8 passed; the older appearance fixture omitted the project ADMIN membership
needed for Edit Project. Its fixture was corrected, retaining the application's
access control. An added public-auth test initially matched both header/footer Sign In links; it
was narrowed to the header. Final current-checkout run: **9/9 UI regressions passed**
(five redesign/auth checks, knowledge review, story generation and two appearance
checks). TypeScript, changed-file lint and `git diff --check` passed. Six legacy,
13 platform, eight knowledge, four count, seven review and 23 feature/history
backend tests passed with doubles: **61 distinct checks**. No real provider calls.

The first isolated onboarding request took about 27 seconds to compile in Next dev;
subsequent warm route requests were much faster. These timings are development
observations, not production benchmarks or proof that all navigation latency is fixed.

## Manual review and remaining scope

Run your normal development API/UI with the existing development configuration.
Review onboarding, project overview, stories, scenarios, testcases, knowledge,
environments and Platform Admin → Prompts in light/dark modes. Use your normal login;
project administrators must not gain platform prompt access. Review both a failed
save and a successful save. Use only synthetic content for model-based checks.

Real development login/provider tests remain manual. Private recording storage,
upload/transcription and the remaining Test Design release gates are still open.
Next prompt phase is a bounded synthetic draft preview, followed by real integration
qualification. Execution MVP is held. No deployment was performed for this local refresh.

## Short action labels (2026-11-13)

Scenario/testcase catalog actions and project overview actions now display Review, Edit and Delete. Context remains in accessible labels and dialog titles; permissions and behavior are unchanged. Saved-draft review buttons use the same concise label. Ten focused catalog/approval UI tests passed with intercepted fixtures; TypeScript, focused lint and whitespace checks passed. These checks do not establish real-login integration.

