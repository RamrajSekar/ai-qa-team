# Selected AI pool and draft public policies

2026-11-16. The Account subscription usage display emphasizes the saved AI mode
for a project. Other AI usage is collapsed by default. With multiple authorized
projects, a selector chooses which project's saved mode to display; the balances
remain account-wide. Null saved configuration means Managed, consistent with the
existing default. Failed or unknown configuration shows both balances explicitly.
Changing the display performs no configuration, usage or billing writes.

## Publication hold

Privacy, Terms and Support pages are prepared at `/privacy`, `/terms`, `/support`.
The user confirmed that `support@aiqa.com` is not a controlled, receiving mailbox.
It is not embedded or published. AIQA is a proposed trading/product name, not a
claim that a registered company exists. Public routes return 404 and footer links
remain absent unless all publication configuration is supplied:

```dotenv
PUBLIC_LEGAL_PAGES_ENABLED=false
PUBLIC_LEGAL_OPERATOR_NAME=
PUBLIC_SUPPORT_EMAIL=
```

These are frontend server/build settings; no public client secret is involved.
Set them only after confirming a real receiving support/privacy mailbox, legal
operator identity and reviewing the drafts. Rebuild/redeploy after enabling.
Do not populate a guessed address or enable publication to satisfy an integration
form. With publication held, these URLs are not ready for Atlassian distribution.

Drafts explain reviewed Jira imports, encrypted tokens versus unencrypted application
knowledge, configured AI/provider processing, manual privacy/deletion requests,
retained history, unknown uniform backup/deletion deadlines and beta limitations.
They do not promise GDPR compliance, enterprise certification, fixed residency,
zero provider retention or end-to-end encryption. Provider, storage-region,
retention, operator/jurisdiction and legal review remain release prerequisites.
This is policy preparation, not a new deletion workflow or a service-level agreement.

Relevant guidance consulted:
- https://developer.atlassian.com/platform/marketplace/data-privacy-guidelines/
- https://developer.atlassian.com/cloud/jira/platform/user-privacy-developer-guide/

Existing Jira implementation and the legacy AI preflight fix are separate pending
work and are not included in this scoped UI/policy pull request. No migration,
allowance reset, model/provider call or legal-page publication is authorized here.

## Verification

Three intercepted browser checks passed: mode selection/collapsed inactive usage
with unchanged counters, unavailable-mode fallback, and unpublished legal routes
and footer links. Source-only TypeScript and changed-file ESLint passed.
No real provider, mail delivery, published legal-page review or production
privacy/deletion workflow was verified. Existing generated Next development
artifacts are excluded from the source-only TypeScript check.

Dashboard refinement: AI allowance meters and the sample AI chart are removed
from Dashboard. Test Cases is shown with the saved total usage and effective
complexity-tier capacity. Account subscription retains the selected-mode display.

Dashboard follow-up verification: all four intercepted browser checks passed,
including a saved Test Cases count of 4/10, no Dashboard AI meters/chart or
AI-configuration reads, and preserved Account usage behavior. Source-only
TypeScript, changed-file ESLint and Git whitespace checks passed.
