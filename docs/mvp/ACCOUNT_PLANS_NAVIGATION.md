# Account plans navigation and model selection

2026-11-22 development follow-up.

View plans opens `/settings/account/plans` within the authenticated workspace,
reusing the public pricing catalogue. Back to account returns to Subscription.
Public pricing remains available anonymously. Public header/footer links show
Open workspace for an existing authenticated user rather than inviting sign-in
again. A valid session is retained; opening pricing never logs a user out, changes
plan/AI configuration, or starts a purchase. Paid checkout remains unavailable.

Model selection uses provider-specific suggestions plus Other model. Saved custom
identifiers remain editable and are never replaced on load. Azure Deployment is
still customer-entered text. Selecting a model does not invoke an API or activate
it. Test Connection and Save & Activate retain their explicit existing behavior.
The list is not a promise of entitlement, price or real-provider qualification.
OpenAI's existing default remains unchanged; legacy choices are labelled. Maintain
suggestions as providers change; manual entry remains available.

Model reference pages checked 2026-11-22:
- https://developers.openai.com/api/docs/models/gpt-4.1-mini
- https://developers.openai.com/api/docs/deprecations
- https://ai.google.dev/gemini-api/docs/models
- https://platform.claude.com/docs/en/models/overview

The Unspecified scenario breakdown is removed from the UI. Existing rows and total
resource usage remain untouched. No backend, billing, approval or migration change.

Verification: isolated production build and TypeScript passed. Scoped ESLint and
`git diff --check` passed. All 28 intercepted-API browser tests passed across
pricing-navigation, byok-providers, ai-usage-display and customer-accounts suites.
They cover guest/signed-in navigation, saved custom models, explicit connection
testing, usage tiles and onboarding. No live model, credential, billing or database
operation was performed. Backend and provider qualification remain unchanged.
