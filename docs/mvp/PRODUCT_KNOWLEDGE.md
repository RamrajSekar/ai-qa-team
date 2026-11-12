# Product knowledge and story design — development slice

Updated 2026-11-11 on `dev`. This is an additive development implementation,
not recording-ingestion or customer-execution readiness.

## Behavior

Project → **Product Knowledge** accepts document text or timestamped transcript
excerpts (timestamps within 30 minutes). Immutable project-scoped sources are
limited to 60,000 characters. Video/audio upload, speech transcription, frames,
OCR, media retention and model training are **not implemented**. Use nonsensitive
product material; do not submit credentials or personal data.

Extraction proposes terminology, roles, rules, workflows, exceptions and unknowns.
Each claim cites an exact quote and source ID; transcripts also cite a segment
with inspectable timestamps. Reviewers edit proposals and clarification answers,
save an immutable snapshot, review its saved content and approve it as project
administrators. Corrections create successors; the active parent is checked at
approval. Observed/inferred/unknown information does not become an expected rule
automatically. Optional teach-back is not implemented here.

In a story, **Analyze with AI** compares acceptance criteria with approved
knowledge. Findings distinguish gaps, ambiguity, missing details and conflicts.
Every blocker needs an explicit reviewed clarification or dismissal rationale.
Changes to the story or active knowledge invalidate the analysis and block new
knowledge-aware generation until reviewed again. A clarification does not silently
change the story or approved knowledge; material source corrections need successors.

New **scenarios** describe WHAT to verify: purpose, role, condition/coverage type,
preconditions, expected outcome and criterion/rule references. They contain no
detailed browser procedures. Approved intents generate draft **test cases** with
HOW: public data, detailed instructions, per-step expected results, assertion
statements, cleanup and context references. Only expected claims may be cited as
expected rules. Separate visual-specification approval remains required before
execution; generated drafts are not executable code or approved versions.

Legacy records remain readable/editable with original steps. Knowledge mode off
preserves existing generation. Knowledge mode on rejects legacy scenario conversion
with instructions to review a new coverage intent; it does not silently upgrade
old data. No historical approvals/results are backfilled. Visual specifications
and previews pin knowledge version/digest and reviewed analysis; changed context
requires successor review.

## Counts and usage

Both scenario UI entry points hardcoded `count=1`. They now offer 1–20 requested
scenarios, default three. The API reports requested, allowed and actual counts.
Plan caps remain. A model can return fewer supported, distinct scenarios; the
service does not invent/clone coverage. Duplicate titles or unsupported references
reject before insertion. Unlimited subscription limits are handled.

Extraction, analysis, scenario design and test design use
`AIUsageService → LLMGateway → ProviderRegistry`: bounded input/output, one AI
credit per request and existing rate/concurrency/subscription reservations.
Knowledge-aware batches do not add a second per-row AI charge. Legacy accounting
is preserved. Usage records add prompt key/version without source text. Credits
are not a dollar spending cap. Object quotas still use legacy count-then-insert
checks; simultaneous generation quota safety is not qualified.

## Configuration and APIs

New Pydantic defaults are off. Development backend configuration:

```dotenv
FEATURES__PRODUCT_KNOWLEDGE=true
FEATURES__STORY_ANALYSIS=true
FEATURES__STORY_MANAGEMENT=true
FEATURES__SCENARIO_GENERATION=true
FEATURES__TEST_GENERATION=true
```

Restart API and refresh UI; verify `/features`. The private local environment
enables both new flags; never commit `.env`. Existing workspace AI configuration
supplies the supported provider; no key/fallback is introduced.

Base `/projects/{project_id}/knowledge`. Membership is mandatory; approval/review
requires project administration. Extra fields reject; validation omits input values.

| Method | Suffix | Purpose |
| --- | --- | --- |
| GET | empty | Latest 100 sources/versions and active version ID |
| POST | `/sources` | Immutable source |
| POST | `/sources/{source_id}/extract` | Metered proposals, no automatic approval |
| POST | `/versions` | Immutable draft snapshot |
| POST | `/versions/{version_id}/approve` | Admin approval after parent check |
| GET | `/stories/{story_id}/analysis` | Latest analysis and computed stale state |
| POST | `/stories/{story_id}/analyze` | New metered analysis |
| POST | `/stories/{story_id}/analysis/{analysis_id}/review` | Reviewed blocker resolutions |

Collections: `product_knowledge_sources`, `product_knowledge_versions`,
`story_analyses`. Mongo `_id` supplies uniqueness. Latest approval uses server
timestamps; concurrent multi-host approval/clock races are not qualified. No vector
or graph store. Production needs pagination, retention/deletion, media protection
and stronger approval-head coordination.

## Verification and manual check

From `ai-qa-team-api`:

```powershell
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_product_knowledge.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_scenario_counts.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_visual_specifications.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_feature_flags.py -v
..\.feature-flags.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_ai_usage.py -v
```

Current: 8 knowledge/design, 4 count, 9 specification/admission, 23 feature/history
and 13 usage checks passed with auth/database/provider doubles. Sandboxed invocation
stalled; completed runs used the existing interpreter outside that sandbox. A
provider-error fixture needed a project membership; authorization was retained.
Read-only development Mongo and Redis pings passed. Pings do not verify writes,
tenancy, login or the full journey.

TypeScript and focused lint passed. New browser regression `tests/product-knowledge.test.cjs`
uses the existing separate Playwright UI tools, not runner dependencies. Start an
isolated Next dev server with `NEXT_PUBLIC_API_URL=http://feature-api.test`, port
3123 and no real `.env`, then from `ai-qa-team-ui`:

```powershell
$env:FEATURE_UI_URL='http://127.0.0.1:3123'
$env:PLAYWRIGHT_MODULE_PATH='C:\path\to\existing\node_modules\playwright'
node --test tests/product-knowledge.test.cjs
```

Auth/API requests are intercepted. Initial attempts exposed cold compilation and
an invalid UTF-8 character introduced during editing; the encoding was corrected.
Those failed attempts remain failures. The final knowledge/story browser regression passed after the fix, as did the
existing legacy story/scenario approval/testcase UI regression. No intercepted
test establishes real-login/Mongo/AI integration. The rerun existing synthetic
admission/binding suite (13) and environment-secrets suite (8) also passed with
doubles: 78 completed backend checks in total.

Manual development check: sign in normally to a dedicated project, add a source,
review/approve its snapshot, add story/criteria, analyze and resolve blockers,
request three scenarios and inspect the actual count. Approve an intent and
generate a detailed case. Approve a knowledge successor and confirm old analyses
and specifications require review. Knowledge/generation/preview must not launch a
browser. See [execution gates](APPROVED_EXECUTION_DELIVERY.md).


## Independent Test Design review checkpoint

The merged NLP review slice adds project-scoped immutable design drafts and project-admin
approval, with approved text/JSON exports for manual use. The catalog's Review & approve
natural-language test design panel pins story, reviewed analysis and knowledge context.
Changed sources mark history stale and require an acknowledged successor review; exports
identify historical staleness. This is separate from visual-execution approval and does
not launch browsers. Per-case compare-and-set coordinates competing approvals; it does
not establish transactional approval across all source collections. Seven synthetic
API/database/auth checks cover versions, exports, stale sources and competing drafts.
Current shared UI styling and its verification limits are in [UI_UX_REFRESH](UI_UX_REFRESH.md).
