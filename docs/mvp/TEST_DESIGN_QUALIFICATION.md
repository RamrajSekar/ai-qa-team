# Test Design qualification — 2026-11-20

**Result: do not sign off Phase 1 yet. Scenario and test-case resource quotas can
be exceeded by concurrent generation requests.** No application behavior, quota
policy, deployed configuration, existing data or execution code was changed by
this verification task.

## Evidence boundaries

- Committed API snapshot: `2f1d6dcd722b511bdd3bf61bf20caa9d1d3eba17`, extracted into
  an isolated directory, without private env files or uncommitted Jira changes.
- MongoDB 8.2.1, separate one-node replica set `qaTestDesign`, loopback port 27129.
  Each run creates a randomly named `qa_test_design_<uuid>` database. Normal unique
  resource/email/project-membership indexes are created only in that database.
- Actual signup/password authentication, signed cookies, persisted account/project
  memberships, project authorization, ASGI routes, review services and MongoDB writes.
- AI responses are deterministic doubles. Session Redis is a LocalCache double.
  These results do not qualify real model output, Redis distribution, network API
  transport, failover durability or provider concurrency/rate enforcement.
- Browser UX tests use a separate isolated Next production build and intercepted
  auth/API responses. They are a separate evidence layer, not a browser connected
  end to end to the Mongo-backed API journey.
- No application database, real AI provider, external account, browser execution
  engine, email, document/image/media processing or production setting was used.

## Backend journey and isolation

The real-Mongo journey passed:

1. Sign up, name the customer account and create a project; creator is project ADMIN.
2. Teach an independently sourced business rule; extract, confirm, save and explicitly
   approve it. The test uses server-assigned rule IDs, never invented references.
3. Create a story, analyze against independently approved knowledge and review it.
4. Generate a scenario using the approved story context, then explicitly approve it.
5. Generate a detailed test case, retain preconditions and exact context, save an
   immutable test design, approve it and export a non-executable manual-use snapshot.
6. Deny another account access to current knowledge, original evidence, historical
   versions, analysis, design state, exports and scenario/test-case lists (eight paths).
   Deny foreign approval as well.
7. Deny same-account users without project membership. Permit authorized TESTER reads
   and explicit test-design approval under the member policy; deny knowledge approval.
   Retrying an approved case preserves the original approver. Deny a foreign platform
   OWNER even with a stale project ADMIN membership.
8. Change the story and verify test-case generation returns 409 before another AI
   invocation. Resource quotas are raised for this check so quota rejection cannot
   falsely stand in for the stale-context safeguard.
9. Verify no execution or ingestion jobs were created.

## Real Mongo concurrency

| Check | Result |
| --- | --- |
| Two different knowledge successors from one parent | Exactly one approval winner and one 409 conflict |
| Repeat approved knowledge with another actor | Original approver/time retained |
| Two saved test-design versions from one active parent | Exactly one CAS approval winner and one 409 conflict |
| Eight simultaneous Managed last-credit reservations | Exactly one reservation; stored Managed usage = 1 |
| Eight simultaneous BYOK last-credit reservations | Exactly one reservation; stored BYOK usage = 1 |
| Two scenario generation requests for one remaining slot | **FAIL: both HTTP 200; inventory and usage become 3 against limit 2** |
| Two test-case requests for one remaining total/basic slot | **FAIL: both HTTP 200; inventory and usage become 3 against limit 2** |

The resource races synchronize deterministic AI responses after both requests have
read availability. This tests resource quota enforcement independently of the AI
concurrency/rate limiter. A default AI concurrency limit is not an atomic resource
reservation and must not be relied on to enforce scenario/test-case storage limits.
Both races reproduced in the working tree and again in the clean committed API
snapshot. Qualification intentionally exits 1 while either resource invariant fails.

The AI credit tests call the real reservation method with MongoDB; they do not
claim that a full live-provider invocation was qualified. One-node tests establish
Mongo atomic conflict behavior, not multi-host failover qualification.

## Root cause and smallest safe remediation

- `app/routes/scenario_routes.py`, `generate_scenarios_from_story`: reads available
  slots, awaits generation, inserts records and increments usage afterwards.
- `app/routes/testcase_routes.py`, `generate_testcases`: the same gap exists for the
  aggregate and per-complexity allowance. Separate atomic increments do not make
  the earlier limit check atomic.
- `app/services/subscription_services.py`, `increment_usage`: unconditional increment
  cannot reserve capacity for an in-flight request.

Follow-up: reserve total output slots atomically in the canonical billing scope
before model work; test cases must reserve both aggregate and complexity capacity
in one atomic operation. Use durable request identity and settlement, charge actual
saved rows, release unused slots only on known outcomes, and reconcile interrupted
or uncertain writes without blind replay. Apply the same discipline to manual
create and legacy writers; audit project/story creation too. Preserve existing
usage, account migration rules, AI-mode counters and versioned approvals. A lock
inside one API process is insufficient. Do not merely serialize fixture AI calls
or change the test to accept oversubscription.

## Reproduction

Start a separate development `mongod` with `--bind_ip 127.0.0.1 --port 27129
--replSet qaTestDesign` and a new private temporary dbpath. Initialize that one-node
replica set. Never point this task at the application database.

From the repository root:

```powershell
.\.feature-flags.venv\Scripts\python.exe -X utf8 `
  ai-qa-team-api/scripts/verify_test_design_qualification.py `
  --confirm-isolated-local --output tmp/test-design-real-results.json
```

The script accepts no remote database URI, hardcodes loopback, verifies the replica
set name and drops only its generated database in `finally`. The caller owns the
separate Mongo process; stop it after verification. No database migration or feature
activation is included. Sanitized results are recorded in
`evidence/test-design-qualification-20261120.json`.

## Existing regression suites

185 tests passed across product knowledge, persistent training, test-design review,
approved-story contexts, requirement contexts, story knowledge changes/proposals,
scenario count reporting, Managed/BYOK allowances, account billing, customer account
isolation and value ownership. These fixture suites did not previously exercise
both resource-generation requests against a simultaneous real-Mongo last slot.

24 browser tests passed in a clean production-build run (55 seconds): catalog
navigation/edit/delete/pagination, precondition editing, admin/member scenario
generation, training three rules then adding/correcting knowledge, clarification
recovery, focus-safe autosave, discard, uncertain extraction and optional/admin-only
test-design approval policy. Browser auth/API responses were intercepted fixtures.

The first production run passed 23/24: the stale-removal test mutated its fixture
before the asynchronous removal request completed. Waiting for the Review removal
heading fixes that synchronization error; the final complete run passed 24/24.
No application code was changed to satisfy it. Earlier attempts during development
startup/route compilation were interrupted and excluded.

Final real-Mongo result: **19 checks passed, two failed**. The exact committed API
snapshot reproduced both quota failures. All generated databases were dropped,
and the separate Mongo process was shut down. Script compilation and Git whitespace
checks passed. Real-provider design quality and a browser-to-live-API journey remain
unqualified; this task must not be read as a full Phase 1 release sign-off.


## 2026-11-21 development checkpoint

The historical last-slot failures below are resolved by the [2026-11-21 resource quota fix](RESOURCE_QUOTA.md) in isolated development qualification. Preserve these original results as the before-fix baseline.
