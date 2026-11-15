# Knowledge security foundation and Ask — 2026-11-15

## Delivery boundary

Ask is implemented behind default-off `knowledge_ask`, using the existing QA Agent
route, model gateway, platform prompts and Managed/BYOK controls. This is not model
training, a new agent framework, RAG/vector search, execution or media ingestion.

The user confirmed that managed keys are not provisioned and requested disabled
preparation. `knowledge_encryption.py` is an isolated envelope/KMS adapter with tests,
NOT an encrypted Mongo storage implementation or data migration. Existing knowledge
remains in its current storage representation. Do not claim application-level
encryption, enterprise confidentiality or production security qualification.

`KNOWLEDGE_ENCRYPTION_REQUIRED=true` currently fails closed in ProductKnowledge;
it blocks normal knowledge operations instead of silently writing plaintext. Keep
it false until a separately reviewed encrypted storage/cutover implementation exists.
Both this setting and `FEATURES__KNOWLEDGE_ASK` were set false in the ignored private
development `.env`; no secrets or environment file are committed.

## Ask behavior

- Authenticated account ownership is reloaded through CustomerAccounts, rather than
  trusting account/role claims supplied by a caller. Active same-account project
  membership is required in addition to the existing route authorization. Platform
  roles do not bypass it. Legacy users/projects must complete account migration.
- Only the exact current approved snapshot and its exact source evidence enter
  context. Pending proposals, foreign projects and historical versions are excluded.
  Source validation happens before the AI call. Up to 60,000 serialized context
  characters are accepted; exceeding the limit rejects without silently truncating.
- Questions are limited to 2,000 characters. No knowledge returns a deterministic
  not-covered response without an AI request. Each provider-backed question is one
  `KNOWLEDGE_ASK` operation, subject to existing allowance/rate/concurrency controls.
  Managed/BYOK is backend-resolved; no silent provider/account fallback.
- Platform OWNER/ADMIN owns `KNOWLEDGE_ASK_V1`. Server instructions constrain even
  a customized task prompt. Claims may be expected, observed, inferred or unknown;
  approval does not silently change that information type.
- Responses must cite existing claim IDs and exact statement excerpts; conflict
  responses require at least two distinct rules. Source references are built by
  trusted code, not model URLs. Unsupported free-form answers are replaced with a
  canonical unknown response. Citation validation is not proof of semantic truth;
  representative real-model quality/prompt-injection evaluation remains a gate.
- Authorization and current knowledge version are rechecked after the provider call.
  Revoked access or changed knowledge prevents returning the answer.
- Provider automatic retries are disabled; the Ask deadline is 90 seconds. A
  deterministic per-account/project request receipt prevents duplicate/concurrent
  submission of the same request ID. There is no automatic whole-question retry.
  A failed/timed-out/interrupted request can consume allowance and stays uncertain.
  Process interruption does not replay it. Metadata receipts have no conversation,
  source text, model answer, credential or raw provider output.
- Questions/answers live in browser memory only, disappear on refresh and are not
  sent again on mount/navigation. An explicit new submission after an uncertain
  outcome requires a warning/confirmation. There is no conversation-history claim.
- Propose correction opens the existing human review flow. Asking never changes
  approved knowledge, approves rules or starts a browser execution.

## Key-service preparation and provisioning

Recommended development provider: Google Cloud KMS, SOFTWARE protection, symmetric
encrypt/decrypt. Create a non-production project, enable KMS, choose an appropriate
region, create a key ring and a key; configure rotation. Keep production resources
and identities separate. Grant a runtime identity CryptoKey Encrypter/Decrypter on
its permitted key, not broad key-administration permissions. On Vercel, configure
and qualify workload identity federation/short-lived credentials separately. No
service-account private-key file is required or checked into this repository.

The adapter accepts an injected short-lived token provider and fixed validated GCP
key resource. It never takes arbitrary endpoints from customers, follows redirects
or falls back to a local master key. Account-to-key mapping must be server-owned.
Use separate permitted customer keys; do not trust a key name stored in a payload.
AES-GCM encrypts payloads with per-envelope random data keys/nonces, and KMS wraps
those keys. Authenticated context binds account, project, collection, record and
format version. Swapping ciphertext between those scopes fails decryption. Errors
are sanitized. No live KMS call was made during this implementation.

Provisioning references:
- https://docs.cloud.google.com/kms/docs/create-key
- https://docs.cloud.google.com/kms/docs/iam
- https://cloud.google.com/kms/pricing

## Required encrypted-storage cutover (not performed)

1. Inventory every plaintext copy: source text/segments, approved/draft claims and
   quotes, review proposals/answers/input, story analyses, derived cases and exports,
   attachments, backups, telemetry and any future indexes. This helper alone protects
   none of these existing records.
2. Choose and review the storage integration (driver CSFLE versus explicit envelope
   repository boundary), account key mapping, permitted metadata leakage and data
   residency. Benchmark read/decrypt latency; do not silently weaken encryption to
   support text/vector search. No embeddings are added by this slice.
3. Complete all-old-writer shutdown from KNOWLEDGE_APPROVAL_COMPATIBILITY.md. Back up
   privately and test restore. Stop writes during migration. Deploy every compatible
   reader/writer before activating an encryption requirement.
4. Dry-run counts and missing-account/reference checks. Migrate through a resumable,
   explicit, reviewed maintenance tool/shadow store. Preserve logical IDs, approved
   content digests, receipts, approval names/times, exact evidence and test/run pins.
   Validate digests after authorized decryption. Never migrate at API startup.
5. Prove Client A/B API/job/export isolation, wrong-key and tamper rejection, no
   plaintext logs/fallback, rotation with retained decryptable key versions, KMS
   revocation/outage, cancellation, rollback and backup restoration. Losing old keys
   can make history unrecoverable; key destruction requires retention review.
6. Define source/review/history deletion policies and audit trails with no sensitive
   content. Ask receipts currently retain only replay-prevention metadata; do not
   delete them in a way that silently permits paid-request replay.

Encryption cannot hide content from an authorized backend performing decryption or
from an AI provider receiving approved context. Customer-approved providers, data
handling/retention terms and minimum disclosure remain separate release gates.

## Configuration and verification

Private backend defaults (UI reads `/features`; no separate public key setting):

```dotenv
FEATURES__KNOWLEDGE_ASK=false
KNOWLEDGE_ENCRYPTION_REQUIRED=false
```

For isolated synthetic development Ask tests, fixtures enable the first flag only.
Do not turn on the encryption requirement as a substitute for the storage cutover.

Backend commands from `ai-qa-team-api`:
```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p 'test_*knowledge*.py' -q
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_ai_usage.py -q
```

Browser prerequisites follow QA_AGENT_TRAINING_M2.md: isolated port-3125 Next server,
`NEXT_PUBLIC_API_URL=http://feature-api.test`, UI-only Playwright module. Run
`node --test --test-concurrency=1 tests/knowledge-ask.test.cjs tests/qa-agent-training.test.cjs tests/pricing.test.cjs`.
Also run TypeScript, focused lint, feature/account regressions and whitespace checks.
Actual results and remaining limitations are recorded in the delivery PR. No claim
of real login/Mongo/KMS/model verification follows from intercepted browser fixtures.

Final local results: 65 knowledge/Ask/encryption/training/disabled-ingestion tests,
15 AI-usage tests, 29 customer-account tests and 23 feature-policy tests passed.
The final browser run passed 14 checks (Ask, training and public pages), including
390px overflow checks. Screenshots of landing/pricing were visually inspected.
Initial verification exposed an existing completion-unmount bug leaving tabs locked;
TrainingReview now clears its parent pending flag on unmount. The initial browser
run was 3/13: three Ask navigations preceded server readiness, six completion-related
training checks exposed that bug, and one pricing check had an ambiguous alert
selector. Those failures were retained, fixed and followed by the passing final run.
Backend fixture corrections concerned a validation field name, the usage telemetry
field `operation_type` and stale feature-map expectations; no checks were removed.
Live KMS, Mongo, provider quality and encryption migration remain NOT RUN.
