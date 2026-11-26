# Pricing Phases 3/4 — usage experience and guarded billing

Implemented for review on 2026-11-26. This is a gated development delivery, not a
paid launch. Free limits stay unchanged. No production account, usage counter,
environment variable or payment configuration was changed. No live charge occurred.
The user's USA business has a new Stripe account; it is not connected by this PR.

## Account experience

Account shows independent Managed/BYOK balances, included users (including owner),
extra users (zero until Phase 5), and the AI period/reset date in UTC. Saved-item
capacity never resets monthly. A known expired monthly AI period is projected for
display without writing/resetting stored usage on navigation; the existing atomic
AI reservation performs actual rollover. Unknown periods show no invented reset.

Inline 80%/100% notices are explicitly dismissible per authenticated user, account,
resource policy or AI month, and threshold. A new month/higher threshold can show a
new notice. Dismissal receipts survive reload; no repeated popup or email is added.
Exhausted AI allowances leave manual editing/review and saved records available.

## Managed money boundary

`managed_spend_guard` defaults false. Activation requires a reviewed cutover ID,
current-period opening USD balances backed by provider evidence, and stopped
writers. `scripts/managed_spend_operations.py` is development/local/test-only,
dry-run by default, with digest-matched apply and immutable receipts. Historical
unknown attribution is included conservatively. No startup/login migration occurs.
Production adoption needs a separate reviewed operational cutover and backup.

Once `ai_spend_control/managed` is initialized, disabling the flag does not bypass
the spend boundary. Provider calls require a single-use durable admission through
the existing gateway; configuration tests/activation also use metering after
cutover. BYOK does not reserve platform provider dollars. Request allowances and
internal dollar budgets remain different controls.

An integer micro-USD reservation holds both account and platform monthly capacity
transactionally. Reserve the qualified model's full published context window plus
bounded output, not a character-based token estimate. The compatibility profile
pins `gpt-4o-mini-2024-07-18` (128,000 context / 16,384 maximum output); other
profiles fail closed. Rates, rate revision, per-request/account/platform ceilings
must be configured and reviewed. This profile does not qualify current model
availability, quality or commercial costs. Provider-reported model identity and
token bounds are checked; no real AI call was used for qualification here.
Existing Pro/Enterprise owners also require explicit budget entries before a global
cutover; missing/unsupported profiles or plans fail closed instead of spending.

Known actual usage settles once; confirmed pre-submission failure releases the
hold. Submitted/uncertain work stays held without TTL or blind retries, including
after restart. Missing tokens remain unknown. Unexpected model/token/cost bounds
halt new Managed calls for review. The private CLI can reconcile an exact pending
reservation from digest-reviewed provider evidence. An over-bound cost anomaly
requires a separately reviewed ledger correction; this CLI cannot silently remove
the halt or increase a reservation. A new month never erases old pending records.

## Payment ownership and portability

Stripe is the initial adapter (`stripe==17.1.0`, pinned API
`2026-11-18.endive`). Provider graph retrieval, SDK objects, signatures and hosted
URLs stay inside `services/billing/stripe_provider.py`. The application owns the
catalogue, saved limits, usage, checkout operations and payment receipts. Each
subscription records its provider; new providers can be added without rewriting
entitlement rules. Existing subscriptions/payment methods still require an
explicit provider migration; portability is not an automatic switch.

Only an authoritative account OWNER/ADMIN can POST checkout/portal. Stored role
and account assignments are reloaded; platform roles do not bypass this boundary.
GET status and pricing are read-only. Prices are server-owned monthly USD Team/
Business identities, validated against the catalogue. Existing accounts require
explicit v2 account/separate-AI adoption; new accounts use v2 only when checkout
and separate allowances are explicitly enabled. Legacy accounts remain intact.

Checkout has a durable account lock, saved contract/price/limits and stable provider
idempotency key/integration identity. An uncertain response keeps the same request;
the UI offers resume, never automatic repurchase. Operations older than the safe
retry window require operator/provider reconciliation. No automatic expiration of
unknown purchases occurs. A verified expired Checkout Session releases a known
pending operation. Unknown sessions need private inspection; no generic public
unlock endpoint is supplied.

Only a signed, recent, mode/API-version-matched provider event, followed by fresh
provider invoice/subscription retrieval and account/customer matching, may grant a
plan. The browser return URL grants nothing. Full initial monthly invoices and
whole-cycle renewals are supported; proration, discounts, trials, annual terms and
plan changes are unavailable. Payment receipt identity is per provider/mode/invoice,
not just event ID. Transactional fences serialize payment/cancellation/refund races.
Cancellation/refund-before-payment tombstones prevent late grants. Duplicate
events cannot refill counters. No raw webhooks, signatures or credentials are
stored/logged; financial receipts retain scoped normalized identifiers/amounts.

### Initial commercial lifecycle policy

- Renewal extends the paid-through date and retains usage; included AI resets on
  the account's UTC calendar month, not on payment, mode change or renewal.
- The billing portal disables subscription updates/proration and permits
  cancellation only at period end. Live checkout also validates that policy.
- Failed payments do not grant time. Already-paid time stays usable; after it
  expires, new consumption is blocked. Saved data/manual review remain available.
- Final cancellation returns to Free limits without deleting records or resetting
  usage. Over-capacity data remains available; new creation obeys Free capacity.
- Refunds/disputes are handled in Stripe by an authorized operator. Events mark
  affected current payments for review and block new paid consumption. No automatic
  request-credit refill, application refund endpoint or deletion is introduced.
- Tax/legal terms are launch gates. Live configuration requires reviewed commercial
  terms, real HTTPS terms/privacy URLs and verified Stripe Tax setup/registrations.
  Live Checkout enables automatic tax and collects billing address/terms consent.
  These declarations do not configure tax registrations or validate legal policy.
- No automatic overage charges, extra seats or request-pack purchases exist yet.

## Private configuration (backend only)

Defaults remain disabled. Never paste values into chat or commit actual secrets.
Configure Stripe keys/webhook signing secret as private sensitive Vercel variables;
test and live keys/price IDs/webhooks are separate. No frontend publishable key is
needed for hosted Checkout.

| Setting | Purpose |
| --- | --- |
| `FEATURES__BILLING_CHECKOUT` | Explicit checkout gate, default false |
| `FEATURES__MANAGED_SPEND_GUARD` | Spend admission gate, default false |
| `FEATURES__CUSTOMER_ACCOUNTS`, `FEATURES__ACCOUNT_SUBSCRIPTIONS`, `FEATURES__SEPARATE_AI_ALLOWANCES` | Required account boundaries |
| `BILLING__MODE` | `test` initially; `live` requires additional launch gates |
| `BILLING__STRIPE_KEY`, `BILLING__STRIPE_WEBHOOK_SECRET` | Private provider credentials |
| `BILLING__STRIPE_PRICE_IDS` | JSON mapping of Team/Business to monthly USD price IDs |
| `BILLING__STRIPE_PORTAL_CONFIGURATION` | Reviewed cancellation-only portal configuration |
| `BILLING__APP_ORIGIN` | Real frontend origin; localhost HTTP development only |
| `BILLING__TERMS_URL`, `BILLING__PRIVACY_URL` | Reviewed public HTTPS policies |
| `BILLING__COMMERCIAL_TERMS_REVIEWED`, `BILLING__TAX_SETUP_VERIFIED`, `BILLING__SANDBOX_QUALIFIED`, `BILLING__LIVE_MODE_APPROVED` | All default false; explicit evidence-backed live gates |
| `MANAGED_SPEND__CUTOVER_ID`, `MANAGED_SPEND__PRICING_REVISION`, `MANAGED_SPEND__RATES_VERIFIED` | Reviewed immutable admission policy identity/rate review |
| `MANAGED_SPEND__MODELS` | JSON snapshot-model map with integer input/output micro-USD per million tokens |
| `MANAGED_SPEND__PER_REQUEST_MICRO_USD`, `MANAGED_SPEND__PLATFORM_MONTHLY_MICRO_USD` | Positive reviewed internal ceilings |
| `MANAGED_SPEND__ACCOUNT_MONTHLY_MICRO_USD` | JSON per-plan internal ceiling map (Free/Team/Business required) |

Webhook route: backend `POST /billing/webhooks/stripe`; configure a snapshot event
destination at the pinned API version for invoice paid/payment failed, subscription
updated/deleted/paused/resumed, checkout completed/async succeeded/expired, charge
refunded and dispute created. Preserve signature verification on the raw body.
Investigate rejected/uncertain events privately; retries must never become a second
purchase or bypass a review tombstone. Payment events remain available for existing
subscriptions when the new-checkout gate is disabled.

## Qualification and remaining launch gates

Current evidence uses disposable loopback Mongo fixtures, intercepted browser APIs
and a separately provisioned **temporary claimable Stripe sandbox**, not the user's
new account. Sandbox credentials/claim URL remain in ignored private CLI state.

- 13 real local Mongo transaction/API checks: last-slot account/platform races,
  single-use calls, measured settlement, uncertain holds, cutover, provider anomaly,
  duplicate payments, out-of-order cancellation/refund, renewal, account roles,
  and pending invitation inventory.
- Seven real Stripe sandbox checks: monthly price, customer idempotency, hosted
  Checkout creation/idempotency, portal policy, test-card paid invoice using the
  current API, period-end cancellation, refund/payment-to-invoice mapping. Fixture
  checkout was expired and synthetic subscription canceled; payment was refunded.
- 93 focused backend checks passed, including seven provider contract/signature
  tests and five usage experience tests alongside existing AI/account/quota/pricing
  regressions. Fourteen browser checks cover persistent
  notices, explicit stable checkout retry, pending resume and member controls.
- Isolated production UI build/TypeScript, scoped ESLint, dependency lock validation
  and `git diff --check` passed; mobile usage screenshot inspected. These are
  synthetic login/API fixtures, not production billing evidence. The main-checkout
  TypeScript command hit pre-existing generated `.next/dev` type/version drift;
  the clean isolated production build validates current source without changing
  the user's local generated files.

Reproduce from `ai-qa-team-api`:

```powershell
..\.feature-flags.venv\Scripts\python.exe scripts/verify_pricing_billing.py --confirm-isolated-local
..\.feature-flags.venv\Scripts\python.exe scripts/verify_stripe_sandbox.py --private-profile <private-claimable-sandbox-profile> --confirm-synthetic-sandbox
```

The first requires the separate loopback `qaTestDesign` replica set on port 27129
and creates/drops only its generated database. The second makes real synthetic
sandbox API operations and refuses a profile without claimable-sandbox identity.
It does not touch the application database or print credentials/hosted URLs.

Before sales: connect the business-owned Stripe sandbox securely; complete hosted
checkout in a browser and verify delivered/retried signed events end to end;
qualify payment decline/timeout/failover and operator reconciliation; review legal
refund/renewal/tax policy and production migrations; measure real supported-model
tokens plus infrastructure/support margins at proposed quotas. No measured price
or model qualification is claimed here. Keep all live gates false until complete.

Next bounded work is business-owned sandbox/live-launch qualification. Phase 5
then adds extra-user purchases and durable independent Managed/BYOK request packs
with explicit expiry/refunds and atomic included-first consumption. Phase 6 keeps
automation and Enterprise pricing separate and dependent on delivered capability.
