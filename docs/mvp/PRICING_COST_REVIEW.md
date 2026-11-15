# Test Design pricing and cost review — 2026-11-15

This is a planning model, not a measured bill or approved paid entitlement. Public
pages are simplified around current Test Design functionality. Prices continue to
come from the existing backend catalogue; no saved limits, billing, balances or
provider/model selections changed.

## Current recommendation

Keep the $1,000 fixed-scope pilot and ~$499 Managed / ~$349 BYOK monthly figures
explicitly indicative while measuring pilots. KMS does not justify a subscription
increase. Neither do low KMS/AI list prices alone justify dropping prices: support,
onboarding, hosting, security and customer value dominate at this stage. The $150
Managed/BYOK gap is a commercial hypothesis, not demonstrated AI cost savings.
Do not launch paid checkout or promise unlimited usage from this review.

Before choosing final amounts, measure 3–5 representative pilot accounts: actual
tokens and models per task, model failures/charge semantics, active users, retention,
API/DB/Redis load, support time, acquisition and willingness to pay. Ask now consumes
the same allowance pool; large-context questions change the task mix. BYOK removes
customer model-token charges from our bill, not platform/support/security costs.

## Official list-price reference points (USD, checked 2026-11-15)

| Component | Reference | Cost treatment |
| --- | --- | --- |
| GCP software KMS | $0.06 per billable key version/month; $0.03 per 10,000 symmetric operations | Ten clients × two versions = $1.20/month; 100,000 total operations add $0.30. Rotated retained versions and usage must be counted. |
| MongoDB Atlas | Flex $8–$30/month; dedicated starts around $60/month | Shared company baseline; dedicated/security/backup capabilities depend on chosen tier/region. Free development infrastructure is not a production budget. |
| Vercel | Pro reference around $20/month plus usage/seat effects | Verify actual paid seats, compute/requests, regions and included credits against the selected plan; frontend/backend are not automatically separate seat fees. |
| Redis (illustrative Upstash option) | $0.20 per 100,000 commands | Provider example only, not a migration recommendation or claim about our current Redis provider. |
| AI | Model-specific input/output token prices | Measure per task; a request is not a fixed token count or dollar guarantee. BYOK provider bill belongs to the customer. |

Sources: [KMS](https://cloud.google.com/kms/pricing),
[Atlas](https://www.mongodb.com/docs/atlas/billing/atlas-flex-costs/),
[Vercel](https://vercel.com/pricing), [Redis example](https://upstash.com/pricing/redis),
[AI model pricing](https://developers.openai.com/api/docs/pricing).
Taxes, FX, logging, storage, egress, backups, email, domain, monitoring, payment fees
and support are additional where applicable. No live company billing was accessed.

## Illustrative unit economics, not forecasts

At an example input/output rate of $0.40/$1.60 per million tokens, a 10,000-input /
2,000-output-token task costs $0.0072; 500 tasks cost $3.60. A 60,000-input /
6,000-output-token task costs $0.0336; 500 cost $16.80. These rates appear on the
GPT-4.1-mini reference listing; this is an arithmetic example, not a model availability
or selection recommendation. See https://developers.openai.com/api/docs/models/gpt-4.1-mini.
Premium models, longer tasks and failures can cost substantially more. Character
limits do not establish token/dollar caps, and cache discounts are not assumed.

Example shared baseline: hosting $20 + database $60 + one million Redis commands $2
and KMS $1.50 = $83.50/month before other expenses/overages. At ten paying accounts,
that allocation is $8.35/account; with one customer it is $83.50. This is not an
actual deployment quote. A hypothetical half-hour of support at an internal $40/hour
adds $20/account; two hours adds $80. Customer count and support expectations can
matter more than cryptographic operation costs.

Formula: monthly account contribution = revenue − allocated platform cost − AI
cost − variable storage/compute/network − support − payment fees. A provisional
80% gross-margin target permits COGS up to $99.80 at $499, or $69.80 at $349. Set
actual commercial targets deliberately; do not present these as measured margins.

## Release decisions still required

- Validate value/prices against pilot feedback; Test Design pricing must not imply
  automation, recording ingestion or enterprise encryption delivery.
- Define paid SKU-to-mode entitlements and enforce them server-side. Existing Pro
  records have both pools; marketing Managed/BYOK cards are not separate paid SKUs.
- Define hard monetary budgets/model allowlists, overage policy, support scope and
  retention before paid activation. Existing request counters alone do not cap cost.
- Revisit requests per plan using measured task mix; never reset usage on a mode
  switch or change stored subscriptions automatically.
