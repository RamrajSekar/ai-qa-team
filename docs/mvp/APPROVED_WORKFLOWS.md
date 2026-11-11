# Approved specifications with optional reusable workflows

Updated 2026-11-10. This replaces the Salesforce-specific Step 3 authoring plan.
Login is a user-authored workflow when a case needs it. Public-page cases need
neither login nor a reusable workflow.

## Implemented scope

The development UI supports a reusable-steps library and per-case visual
specifications under Project → Test Cases. Users author ordered navigation,
visible-target click, text entry and exact-visible-text assertion steps. They can
link approved reusable workflow versions anywhere in a specification. No scripts,
selectors, shell commands, unrestricted Robot keywords or JavaScript are accepted.

This slice implements authoring, approval, dependency review and compiled previews.
It has no general browser dispatcher or runtime interpreter. Existing synthetic
execution remains a separate fixed-sample adapter. A compiled preview explicitly
returns execution_ready=false. No browser, model or credential resolver is invoked.

## Version and approval rules

- Each save creates an immutable draft version. A project administrator approves
  the saved version. Approval changes lifecycle metadata once, without editing
  content. Further edits create successors; previous approvals remain stored.
- Reusable workflows have stable workflow IDs and exact version IDs. They infer
  required public parameters from their parameter references. Callers must bind
  exactly those inputs using public values or environment credential references.
- Reusable workflows cannot call other workflows. Workflow approval requires an
  explicit assertion. A test specification can use inline steps only or mix them
  with workflow calls. Its expanded form requires an explicit assertion to approve.
- Workflow definitions are bounded to 20 steps. Specifications are bounded to 40
  entries and 40 expanded steps. Calls do not bypass that bound.
- Specifications pin their story, scenario, legacy case source digest and exact
  workflow version/content digests. Existing legacy generation and code fields
  remain separate. A legacy generated case is not a visual-specification approval.
- Approving a workflow successor makes dependent specifications require review.
  This is computed on current-state reads and preview. Open UI panels refresh when
  the library approves a successor. Draft successors do not supersede approvals.
- Changes to story/scenario/test content require a successor specification. These
  checks fail before preview or future execution. New specification records also
  protect their source cases/scenarios against ordinary catalog deletion.

## Inputs and credentials

Text-entry values are one of public text, a named reusable input, or a reference to
the selected environment role's username/password. Public values are stored with
the specification, so customer credentials belong in environment secret storage.
Credential values never appear in compiled previews. No credentials are decrypted
by this authoring path.

A specification with no credential references previews with no role. A specification
with credential references requires a saved role; password references require its
encrypted configured password. Role choice belongs to the user. Navigation paths
are relative to the selected environment and reject alternate origins, traversal,
query strings and fragments.

## Environment and execution boundaries

Preview pins the exact specification version, expanded workflow references,
environment revision/keyed digest, canonical URL and optional role/credential ID.
The environment is resolved within the authorized project. It opens no URL.

The existing Salesforce Sandbox preparation URL policy remains in force for
environment previews until target authorization and DNS/redirect/subresource/egress
enforcement are implemented. Workflow definitions themselves have no application-
specific login behavior. Supporting other destinations and selecting browser
hosting/vision processing are explicit later changes.

The approved specification is persisted in Mongo; the expanded preview manifest is
not yet admitted to a durable general execution queue. Current Step 2 synthetic
approval/binding records are preserved and are not silently reinterpreted as these
new specifications. A later dispatcher must revalidate exact approvals, sources,
workflow references, environment revision, target policy and permissions immediately
before dispatch, then resolve credentials only inside trusted runtime code.

## APIs and configuration

Default-off backend flag `reusable_workflows` gates API and service operations.
The local backend .env enables it using `FEATURES__REUSABLE_WORKFLOWS=true`.
APIs are development-only. Every project reference requires membership and approval
requires project administration. Validation responses omit submitted values.

The base is `/projects/{project_id}/visual-specifications`.

| Method | Path | Action |
| --- | --- | --- |
| GET | `/workflows` | Latest 100 workflow version records for this project. |
| POST | `/workflows` | Save a new workflow or successor draft. |
| POST | `/workflows/{version_id}/approve` | Approve an immutable workflow version. |
| GET | `/cases/{testcase_id}` | Latest specification with computed review status. |
| POST | `/cases/{testcase_id}` | Save a successor specification draft. |
| POST | `/cases/{testcase_id}/{version_id}/approve` | Approve the saved specification. |
| POST | `/cases/{testcase_id}/{version_id}/preview` | Compile and validate the current approved version for an environment. |

Collections are `visual_workflow_versions` and `visual_test_spec_versions`.
Version IDs use Mongo's unique _id. Approval is a conditional draft-to-approved
single-document transition. Latest approval ordering uses server timestamps.
Multi-host clock/approval races, production index sizing, entitlement and storage
budgets are not qualified by this local slice.

## Manual development check

1. Restart the API after enabling the flag and refresh the UI.
2. In Test Cases, open Reusable steps library. Add a workflow with steps and an
   explicit assertion, save a draft, review its saved steps, then approve it.
3. On a case linked to an approved scenario/story, open Visual execution
   specification. Add inline steps or choose the approved reusable version.
   Bind any named inputs, save, review the saved version and approve it.
4. Select an environment. Choose no role for a public-page case, or a saved role
   for credential steps. Preview the compiled steps. No browser should launch.
5. Approve a successor workflow version. The dependent specification should show
   Review required and reject preview until explicitly recreated/reviewed.

## Remaining Step 3 and Step 4 work

Implement and qualify a trusted runtime interpreter against an approved browser
arrangement. It must locate targets visually, perform only allowed actions, verify
checkpoints, evaluate assertions independently and stop safely on ambiguity.
Then verify cancellation, redacted evidence, positive/negative outcomes, timeouts
after consequential actions without replay, and failure cleanup with real services.
Authoring and mocked compilation tests do not establish those runtime capabilities.

## Verification recorded for this local slice

Eight new ASGI authoring/compilation tests passed with synthetic authentication and
in-memory database doubles. They cover optional public-page execution preparation,
credential references without resolution, exact reusable versions and parameters,
approval gates, successor invalidation, immutable snapshots, expansion bounds,
source changes, project isolation and validation redaction. The preview digest is
checked against the canonical serialized manifest. Approval stores the acceptance
criteria snapshot for review alongside the source digest.

The existing 23 feature/history, 13 approved-run/binding and 8 credential tests also
passed in this task. TypeScript, focused lint on the four affected UI components
and git diff --check passed. No real UI login, MongoDB, provider, browser workflow,
network enforcement, cancellation or evidence-redaction test was run for the new
specifications. These are authoring/preview checks, not runtime verification.

From ai-qa-team-api, run
`..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_specifications.py -v`.
From ai-qa-team-ui, run `node node_modules/typescript/bin/tsc --noEmit --incremental false`
and focused ESLint against VisualStepEditor.tsx, VisualSpecificationPanel.tsx,
ProjectTestCatalog.tsx and FeatureFlagsProvider.tsx. The local .env change is private;
no commit or push was performed by this implementation task.
