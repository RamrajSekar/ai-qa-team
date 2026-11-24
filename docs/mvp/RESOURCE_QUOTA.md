# Scenario and test-case capacity reservations

## Feature-policy fixture repair (2026-11-24)

The three previously failing feature-policy tests now use asynchronous Mongo
session/receipt doubles while executing the real ResourceQuota callbacks. The
generation test accounts for transactional total/tier recounts and verifies usage
is written once by quota persistence, without the former separate increment.
Successful saves and provider authentication failures verify settled reservations
and zero pending slots. An additional test rejects a manual draft when preflight
sees capacity but the transactional recount sees exhaustion, with no resource or
reservation insert. No application behavior, entitlement, migration or usage reset
changed.

Verification: all 25 feature-policy tests, four resource-quota contract tests and
eight Free test-case allowance tests passed in isolation. These doubles do not
qualify real Mongo rollback, concurrency or production behavior.

Development checkpoint: 2026-11-21. Resolves the last-slot races recorded in
[qualification](TEST_DESIGN_QUALIFICATION.md); historical failure evidence is retained.

## Behavior

Manual creation, story/recording scenario generation and test-case generation now
reserve capacity before generation. Mongo transactions atomically hold pending
slots, then insert each saved resource with its usage update. Test cases reserve
both the aggregate and selected complexity allowance. Unused slots are released
on partial output or known failure. Models never run inside a transaction.

A durable `resource_quota_reservations` receipt records admission and saved item
identities. The UI supplies a request identity for each intentional generation;
refresh retries retain it. Repeated admissions return 409 before calling AI.
Old clients without this field remain accepted and quota constrained, but repeated
intentional submissions are separate requests. Never repeat an uncertain model call.
Existing ObjectId resource identities and saved approval/history contracts remain.
Managed/BYOK AI counters are separate and are not reset or refunded by slot recovery.

A stopped process or database outage conservatively retains pending capacity.
Receipts do not expire automatically. Development recovery is explicit:

```powershell
python scripts/reconcile_resource_quota.py --reservation-id <receipt-id>
python scripts/reconcile_resource_quota.py --reservation-id <receipt-id> --apply --confirm-close --plan-digest <fresh-digest>
```

Inspect the dry-run first. Applying closes remaining writes; it preserves saved
rows and does not replay or cancel a provider request. Changed receipts reject a
stale plan. This tool is restricted to development/local/test environments.

## Deployment prerequisites and boundaries

Mongo must support transactions (replica set or appropriate managed deployment).
Standalone Mongo fails creation closed with 503, without reserving capacity.
No existing-data migration, recount, usage reset or startup migration is added.
New receipt collection and pending fields are written lazily; database roles and
schema validators must permit them. The default unique `_id` index provides
receipt uniqueness; do not add a TTL that permits reusing an uncertain request.

Stop old creation writers and deploy all adapted API writers together. Old
backends ignore pending counters and can bypass this mechanism. No shared or
production cutover was performed. Preserve the independent knowledge backend
cutover prerequisite.

`integration_service.import_playwright_tests` remains a legacy direct writer,
behind the default-off `playwright_repo_adapter`. Do not enable it before adding
and qualifying quota admission. Project/story last-slot races and multi-host
failover remain separate qualification work. This is not commercial readiness.

## Verification

- 189 isolated backend quota, knowledge, context, approval, allowance and ownership tests passed.
- Clean committed API snapshot plus this task's overlays: 24 real loopback Mongo
  journey checks and 12 quota/fault/recovery checks passed. They cover last-slot
  AI/AI and manual/AI contention, partial output, rollback, lost acknowledgement,
  replay prevention, legacy users and independent customers. Providers are doubles.
- Standalone Mongo safety probe passed: 503, no receipt or usage mutation.
- 13 client refresh/proxy checks passed, including preserved request identity.
- Production UI build/TypeScript and scoped ESLint passed. All 22 intercepted-API
  browser tests passed, including approvals, generation, plain statuses, tiles,
  provider selection and the plan link. These do not prove live provider access.

## UI follow-ups in this slice

Catalog status cells show plain status; story basis remains inspectable in review
without altering safeguards. Account AI usage uses two responsive tiles and a
CURRENT badge only on the saved selected mode. Unknown configuration is never
assumed to be Managed. Both balances remain intact.

BYOK adds Google Gemini via its fixed official OpenAI-compatible endpoint and
Anthropic Claude via the native Messages endpoint with structured output. Existing
project authorization, encrypted credentials, gateway metering and response
validation remain authoritative. No arbitrary endpoints, fallback providers or
new automatic retries are added. Users enter an available model identifier and
explicitly test/activate it. Live model/key qualification remains outstanding.
References: [Gemini](https://ai.google.dev/gemini-api/docs/openai),
[Claude structured output](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
Four adapter contract tests and 13 existing configuration tests passed with mocks.

Account Subscription exposes View plans. Pricing remains indicative; online paid
upgrades, checkout and automatic entitlement changes are not delivered.
