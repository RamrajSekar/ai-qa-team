# Staging login preparation

Updated 2026-11-10. Steps 1 and 2 are implemented. Login execution and its
qualification remain pending. The selected first target is Salesforce Sandbox.

## Step 1 — environment secrets

New and updated environments store passwords and authorization tokens in an
AES-GCM envelope within the environment's Mongo document. Associated data binds
the envelope to its project and environment IDs. Public responses return blank
passwords, null tokens and configured markers. They do not decrypt the envelope.
Usernames, application roles and non-secret notes remain project metadata.

Blank password edits preserve the saved credential by stable identity. Replacing
a password rotates its value. A username change requires re-entry of a saved
password. Removing a credential row revokes that role. The Auth tab supports
explicit token removal. Revision checks reject stale edits. Secret ciphertext and
metadata change in the same document, avoiding separate-secret write/cleanup races.

Legacy plaintext environment records are masked on read and encrypted on their
next authorized save. There is no bulk migration or retroactive cleanup of existing
history, jobs, backups, notes or variables. Notes and variables are not secret
storage. The existing legacy executor rejects protected environments before
persistence because its job format copies credential values.

The internal runtime resolver requires project membership and an exact environment
and role. It has no API endpoint and is not connected to execution in this slice.
Validation error responses omit submitted values.

Configure an optional `ENVIRONMENT_SECRET_MASTER_KEY`, a URL-safe base64-encoded
32-byte key. If absent, the existing `LLM_SECRET_MASTER_KEY` is used. Preserve the
selected key securely across restarts/deployments. Adding a dedicated key after
envelopes exist, or changing the selected key, requires a separately planned
rotation/migration. This implementation does not implement multi-key rotation.

## Step 2 — immutable input binding

The project overview's **Staging login preparation** section binds an environment
and application role to the selected approved test version. It creates a separate,
immutable `approved_staging_bindings` document, with `execution_ready=false`.

Snapshots pin the canonical URL/origin, target-policy identity, environment
revision/keyed digest, role/credential ID, approved version/content digest and
source digest. They contain no usernames, passwords, tokens, ciphertext, notes,
variables or raw environment document. Preparation does not resolve credentials.

The accepted preparation URL is HTTPS `test.salesforce.com`, with default/443 port
and root or `/login` path. An exact hostname without a scheme normalizes to HTTPS.
Other hosts/ports, embedded credentials, query strings, fragments, whitespace and
backslashes reject. This is string validation; browser DNS, redirects, subresources
and egress enforcement remain pending.

All endpoints below use the existing development-only admission feature gate and
project membership authorization. Their base is
`/projects/{project_id}/approved-visual-runs`.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/staging-bindings/preview` | Resolve an approved version, environment and application role. |
| POST | `/staging-bindings` | Save the returned digest with an idempotency key. |
| GET | `/staging-bindings/{binding_id}` | Return the original snapshot and current/stale validation. |
| GET | `/staging-bindings/testcases/{testcase_id}` | Restore the most recent binding for the project/case. |

Matching retries return the original record. Reusing an idempotency key with
different input rejects. Environment/credential, source or active-approval changes
make a binding stale. Revalidation preserves the snapshot and requires explicit
new preparation. A current result is a sampled check, not a reservation or a
guarantee of future dispatch validity. Mongo's unique `_id` prevents duplicate
binding documents. Multi-host mutation/approval atomicity is unqualified.

Existing approved versions still describe the bounded synthetic sequence. Binding
their identities does not approve login actions. There is no staging start endpoint,
queue consumer, browser launch or provider call. Binding IDs cannot start through
the synthetic run endpoint. The existing synthetic run contract remains unchanged.

## Local verification

From `ai-qa-team-api`, using the existing development environment on Windows:

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_environment_secrets.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_approved_visual_runs.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_feature_flags.py -v
```

The local checkout passed 8 credential tests, 13 approved-run/binding tests and
23 feature/history tests using synthetic database/authentication doubles. TypeScript,
focused environment/onboarding/binding lint and `git diff --check` passed. Encryption
configuration was checked for key presence/32-byte decoding without printing values.
Real UI/Mongo, Salesforce, provider traffic, credentialed cancellation and evidence
redaction have not been verified. These checks establish no production readiness.

To review through the UI, restart the API and refresh the project overview. Save
an environment with encrypted synthetic credentials, select an approved case, then
select environment/role, preview and save the staging binding. Refresh its validation
after an environment edit to confirm stale detection. No browser should launch.

## Remaining ordered work

3. Define and review one bounded login specification with explicit expected results,
   permitted redirects and allowed actions. Decide browser hosting and image
   processing permissions before wiring execution. Bindings must be revalidated
   before dispatch and credentials resolved only inside trusted runtime code.
4. Qualify cancellation/cleanup, secret-safe evidence, positive and negative
   assertions, ambiguous submit handling without replay, failures and project
   evidence access against authorized synthetic staging data.
