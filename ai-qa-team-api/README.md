###Activate poetry
py -m poetry env activate

###Deactivate
deactivate

Start Backend
cd ai-qa-team-api
py -m poetry run uvicorn app.main:app --reload

##Redis is only useful once you start adding background jobs, caching, and async test-execution orchestration.

## Centralized feature flags

Feature policy is part of `app.config.Settings.features` (Pydantic), with no
MongoDB or Redis flag storage. `GET /features` returns only the boolean policy map
and uses `Cache-Control: no-store`. It is public and contains no configuration
values or secrets. A true policy flag does **not** indicate implementation or
readiness: Robot discovery, Test Registry, and test-data generation are not
implemented by this change and no placeholder routes are provided.

Defaults:

```ini
FEATURES__STORY_MANAGEMENT=false
FEATURES__SCENARIO_GENERATION=false
FEATURES__TEST_GENERATION=false
FEATURES__RECORDER=false
FEATURES__NATIVE_EXECUTION=false
FEATURES__JIRA_TRIGGER=false
FEATURES__FAILURE_DIAGNOSTICS=false
FEATURES__SELF_HEALING=false
FEATURES__PLAYWRIGHT_REPO_ADAPTER=false
FEATURES__SELENIUM_REPO_ADAPTER=false
FEATURES__REPOSITORY_DISCOVERY=true
FEATURES__TEST_REGISTRY=true
FEATURES__TEST_DATA_GENERATION=true
```

Set overrides in the API's existing `.env` or process environment. Pydantic also
accepts a JSON `FEATURES` value. Restart **all API and worker processes** with the
same configuration after changing flags, then reload the UI. This is startup
configuration, not a live kill switch for in-flight requests or running tests.
The UI consumes the API map; it does not require duplicate build-time flags.
Deploy the API endpoint before the UI; a missing/invalid/unavailable map leaves
legacy features unavailable while core pages remain accessible.

Disabled Story, Scenario and Recorder routers remain registered but are omitted
from OpenAPI. Direct requests return HTTP 403, for example:

```json
{"detail":{"code":"feature_disabled","feature":"recorder","message":"Feature 'recorder' is disabled."}}
```

Flag checks run before quota/authentication dependencies on disabled operations,
so rejection does not create subscriptions, consume usage, invoke AI, write Mongo
records, or enqueue Redis jobs. Authentication and ownership checks on enabled
operations are unchanged. Scenario generation from a Story additionally requires
Story management; generation from a recording also requires Recorder. Legacy
Playwright import requires **all four** of `playwright_repo_adapter`,
`story_management`, `scenario_generation`, and `test_generation`, regardless of
`repository_discovery` policy. Provider repository listing and OAuth remain available.

`native_execution=false` blocks single/batch requests, execution-record creation,
and both enqueue paths. A disabled worker exits successfully **before polling or
removing any Redis job**. Existing jobs are retained and can resume once execution
is explicitly enabled and the worker restarted. Supervisors should not continually
restart a deliberately disabled worker. GET execution history and its ownership
checks remain available. Existing testcase read/edit APIs are also retained; only
test generation is gated. The dormant generator router remains unregistered.

No collections, documents, queue entries, runner code or legacy feature source
are removed. No data migration is required. Existing clients of disabled actions
must handle the new 403 response or explicitly enable the relevant flags. Enabling
a flag restores access to the existing implementation; it does not repair existing
unfinished features. AI generation no longer initializes an unused OpenAI client
at application import, so a disabled deployment can start without an AI key.

### Validation

Backend tests use `unittest`, FastAPI TestClient, and isolated Mongo/Redis/AI test
doubles. They do not connect to live services. From the API directory, using an
environment with the application dependencies and `httpx` installed:

```sh
python -X utf8 -m unittest discover -s tests -v
```

UI checks (from the UI directory):

```sh
npx tsc --noEmit --incremental false
```

Browser regression tests use Node's built-in test runner and Playwright with a
headless Edge installation. In a separate terminal, start an isolated UI server
with `NEXT_PUBLIC_API_URL=http://feature-api.test`:

```sh
npx next dev --webpack --hostname 127.0.0.1 --port 3107
node --test tests/feature-flags.test.cjs
```

The tests intercept that API origin; no backend is used. If Playwright is installed
elsewhere, set `PLAYWRIGHT_MODULE_PATH` to its module directory. Optionally set
`FEATURE_UI_URL` or `PLAYWRIGHT_CHANNEL` (default `msedge`). Do not point the tests
at a production UI or use a different API origin.

### Deferred follow-up

Existing environment credentials are still embedded in models, execution payloads,
responses and debug logging. Credential references/redaction require a separate
change. This feature-flag patch does not redesign secrets or implement Robot
scanning, TestContract, the data engine, or RunnerAdapter. Existing generator and
other legacy implementation defects are likewise outside this patch.

### Files in the feature-flag change

Backend:

```text
ai-qa-team-api/app/config.py
ai-qa-team-api/app/main.py
ai-qa-team-api/app/utils/feature_flags.py (new)
ai-qa-team-api/app/utils/execution_queue.py
ai-qa-team-api/app/routes/scenario_routes.py
ai-qa-team-api/app/routes/testcase_routes.py
ai-qa-team-api/app/routes/generate-tests.py
ai-qa-team-api/app/routes/test_execution_routes.py
ai-qa-team-api/app/routes/integration_routes.py
ai-qa-team-api/app/services/execution_engine.py
ai-qa-team-api/app/workers/execution_worker.py
ai-qa-team-api/tests/test_feature_flags.py (new)
ai-qa-team-api/README.md
```

UI:

```text
ai-qa-team-ui/src/components/providers/FeatureFlagsProvider.tsx (new)
ai-qa-team-ui/src/app/(app)/layout.tsx
ai-qa-team-ui/src/components/layout/Sidebar.tsx
ai-qa-team-ui/src/app/(app)/projects/[projectId]/page.tsx
ai-qa-team-ui/src/app/(app)/dashboard/page.tsx
ai-qa-team-ui/src/app/(app)/projects/[projectId]/stories/page.tsx
ai-qa-team-ui/src/app/(app)/projects/[projectId]/stories/[storyId]/page.tsx
ai-qa-team-ui/src/components/onboarding/steps/StepTestImport.tsx
ai-qa-team-ui/src/components/integrations/RepoImportModal.tsx
ai-qa-team-ui/src/components/onboarding/steps/StepFinish.tsx
ai-qa-team-ui/tests/feature-flags.test.cjs (new)
```
