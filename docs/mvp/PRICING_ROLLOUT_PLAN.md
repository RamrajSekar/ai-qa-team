# Pricing redesign and commercial rollout plan

Phase 1 merged; Phase 2 implemented for review, 2026-11-26. Paid offers remain planned.
This document changes no live prices, entitlements,
subscriptions, environment settings or billing. Begin with the pricing page;
payment collection and automation remain later delivery stages.

## Proposed catalogue for review

USD per account per month. Every user total includes the owner. Saved-item limits
are shared across account projects and all complexities; they do not reset monthly.
Managed and BYOK are independent monthly allowances, not separate subscriptions.

| Allowance | Free: retain current limits | Team: proposed | Business: proposed |
| --- | ---: | ---: | ---: |
| Monthly price | $0 | $49 | $149 |
| Total users | 3 | 5 | 15 |
| Projects | 1 | 5 | 20 |
| Stories | 5 | 200 | 1,000 |
| Scenarios | 10 | 1,000 | 5,000 |
| Test cases | 10 | 3,000 | 15,000 |
| Managed requests/month | 50 | 500 | 2,000 |
| BYOK requests/month | 50 | 500 | 2,000 |

Enterprise: Contact us, with explicitly contracted capacity and only delivered
capabilities. Do not advertise SSO, SLA, self-hosting, recording ingestion or
general automated execution as available before qualification.

Proposed paid-plan extras: $8 per additional user/month; 500 additional Managed
requests for $10; 500 additional BYOK requests for $5. These are pricing hypotheses,
not approved cost guarantees. BYOK provider charges are paid separately. Pack
prices, expiry/refund policy and tax treatment need validation before sales.

## Phase 1 — Pricing page redesign (first PR)

1. Replace the Managed/BYOK plan split with Free, Team, Business and Enterprise
   cards. Highlight Team visually without an unsubstantiated popularity claim.
2. Use short descriptions, monthly account prices and users including owner.
   Add a scannable comparison for projects, stories, scenarios, test cases and the
   two monthly AI allowances. Explain that AI requests can produce multiple items.
3. Show additional-seat and additional-AI pricing as planned, unavailable to buy.
   Keep automation separately labelled as future optional execution pricing.
4. Retain a brief Managed/BYOK explanation rather than an AI-mode pricing toggle.
   Omit annual discounts until billing/renewal terms are decided.
5. Reuse one catalogue and component on public /pricing, the landing-page pricing
   surface and Account > View plans. Prices/limits come from validated backend
   configuration, never duplicated frontend constants.
6. Add a versioned experimental catalogue with planned Team/Business offers and
   billing_enabled=false. Preserve existing catalogue fields/callers during the
   transition. Publishing an offer must not activate it on an account.
7. Free CTA opens signup for anonymous users; signed-in users remain in the
   workspace. Paid/Enterprise CTAs use a real configured contact/waitlist path,
   or a clear unavailable state if none exists. No fake upgrade or payment action.
   Existing Pro/Enterprise accounts must not be relabelled or migrated silently.

Acceptance: consistent values across public/workspace views; mobile and keyboard
usability; working signed-in/out navigation; honest planned-offer labels; error and
retry states; no checkout, subscription mutation or AI call on navigation. Keep
existing Free entitlements and stored usage unchanged. Deliver a reviewable visual
before proceeding to paid-plan enforcement.

## Phase 2 — Versioned catalogue and account entitlements

Add a distinct Business tier to canonical models/configuration. Preserve free,
pro and enterprise compatibility; decide an explicit Pro-to-Team display/migration
mapping rather than reusing Enterprise for Business. Keep prices and default
allowances configurable through validated backend environment settings.

Unify paid test-case capacity across complexities. Translate total user counts to
the existing owner-plus-additional-members representation (5 total means 4
additional). Invitations reserve capacity; each identity counts once across roles
and projects. Authorize and enforce every limit server-side, including concurrent
last-slot creation. Prepare dry-run, conditional migrations; never migrate/reset
usage during login, startup, plan display or provider-mode changes.

Acceptance: account isolation, legacy compatibility, concurrency, upgrade/downgrade
and mixed-complexity tests; reviewed existing-account migration plan. Downgrades
must not delete data. Decide the over-capacity read/edit/create policy explicitly.

## Phase 3 — Account plan and usage experience

Show current plan, included/extra seats, saved-item capacity and separate Managed/
BYOK monthly balances. Add one-time 80%/100% allowance notices without repeated
popups. Reaching an AI limit blocks AI operations; manual editing, existing data
and reviews remain available. Paid actions remain unavailable until Phase 4.

## Phase 4 — Paid launch prerequisites and checkout

Implement atomic internal Managed spend reservations, supported-model bounds and
account/platform budgets before charging for included Managed usage or packs.
Settle known actual usage; retain/reconcile uncertain provider spend without blind
retries. Validate proposed prices with measured tokens, infrastructure and support.

Integrate checkout using server-owned price identities, verified idempotent payment
events and account-admin authorization. Only verified billing events may grant
paid entitlements. Define tax, refunds, cancellations, renewal, failed payment and
proration. No automatic overage charges. Qualify real payment/provider failure
paths before enabling public purchases. Keep self-service sales disabled until
these gates pass; earlier pages remain an early-access proposal.

## Phase 5 — Additional seats and AI request packs

Sell seat additions through confirmed, transparent billing changes; preserve
unique-identity/pending-invitation capacity enforcement and account usage.

Track purchased Managed/BYOK requests in separate durable balances, with receipt
identity and expiry policy. Monthly rollover resets only included allowances.
Consume included capacity first, then eligible purchased capacity atomically;
duplicate webhooks/retries cannot grant or spend twice. Never confuse an ordinary
provider-mode switch with a purchase or refill. Reuse gateway metering rather
than allowing a frontend counter to grant capacity.

## Phase 6 — Automation and enterprise (after qualification)

Keep Test Design pricing independent from optional execution. Measure browser and
container time, execution-specific AI, evidence retention, cleanup, failure handling
and concurrency before choosing execution prices. Define customer-visible units,
queue/cancellation/provider-failure treatment and explicit overage purchases.
BYOK does not remove infrastructure costs. Execution requires its own qualified
capacity, action, budget and approval controls; a pricing page enables none of it.

## Delivery and decision gates

Sequence separate PRs by phase; Phase 3 is next after Phase 2 review. Check the previous PR's
merge state and current main before each PR. Run targeted API/UI regressions,
production build/types and visual desktop/mobile checks appropriate to the change.
Record actual results and remaining limits; do not substitute mocked billing or
provider checks for real qualification.

Before paid activation, confirm the proposed prices/quotas, effective date and
existing-customer treatment; contact destination; extra-seat proration; pack
expiry/refunds; and measured cost ceilings. These decisions do not block an
explicitly experimental pricing-page redesign.

Current implementation: components/marketing/Pricing.tsx is shared by public
/pricing and workspace /settings/account/plans. GET /auth/pricing exposes the v2
account offer catalogue with billing disabled. Canonical models now accept
free/pro/enterprise/team/business; v2 adoption is explicit and reviewed. Checkout,
seat purchases, top-up balances and hard monetary budgets are not delivered.

See AI_ALLOWANCES_PRICING.md, ACCOUNT_TEAM_BILLING.md, PRICING_COST_REVIEW.md and
TEST_DESIGN_MVP.md for preserved billing, isolation and release boundaries.

## Phase 1 review evidence (2026-11-26)

Public and workspace pages use one API catalogue. Planned paid prices/quotas and
add-ons are configuration-backed display data only; legacy fields and canonical
subscriptions are preserved. The API must be deployed before the v2 UI.

Validation: four isolated catalogue tests and 13 existing allowance tests passed
(the latter with their expected Free Managed setting of 25). Eight intercepted
browser checks passed against an isolated production UI build, covering account
navigation, four plans, mobile overflow, retry, configured prices/contact and
unsafe contact rejection. Changed-component lint passed; desktop and mobile
screenshots were inspected. No production account, payment or provider was used.

Phases 3 onward remain unimplemented. These checks do not qualify paid billing
or validate the proposed prices against real support/AI costs.


## Phase 2 review status (2026-11-26)

See [versioned entitlements](PRICING_ENTITLEMENTS_V2.md) for exact behavior,
development migration instructions, current checks, compatibility and the remaining
Phase 3–6 roadmap. No production migration or paid activation was performed.
