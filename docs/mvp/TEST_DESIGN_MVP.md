# Phase 1 — Test Design MVP release gates

Current delivery priority: finish Test Design before advancing the Execution MVP.
The existing execution implementations, flags, data and histories remain preserved.
No product readiness claim follows from a synthetic browser or mocked API check.

| Capability | Current state and release gate |
| --- | --- |
| Project onboarding | Existing account/project setup; refreshed UI. Real development login/manual journey still required. |
| Product learning | Document/timestamped-transcript sources and reviewed snapshots exist. This is durable project memory, not LLM fine-tuning. |
| Narrated recording intake | NOT IMPLEMENTED. Private storage is not available; upload/transcription/media handling and deletion/security tests remain required for the original scope. |
| Knowledge governance | Human approval, expected/observed/inferred/unknown separation and successors exist. Multi-host approval-head coordination remains unqualified. |
| Story analysis | Gaps, ambiguity, missing detail, conflict review and stale-context checks exist behind flags. Real supported-model checks remain. |
| Scenarios | Knowledge-aware coverage intents describe WHAT; legacy records remain readable. Requested/allowed/actual counts exposed. |
| Detailed testcase design | NLP instructions, explicit expectations/assertions, data and rule/criterion links exist. Human review is required. |
| Review/export | Immutable NLP drafts and per-case CAS approval, manual-use text/JSON exports; source changes require review. No automation begins. |
| Prompt governance | Platform OWNER/ADMIN only, configured via backend owner bootstrap. Phase 2 legacy migration is implemented; synthetic draft model preview and normal-login qualification remain. |
| Usage and limits | Existing credits/rate limits retained. Not a proven dollar budget; concurrent generation quota safety remains unqualified. |
| Pilot qualification | Real user journey, representative design-quality review, privacy/isolation, retention and recording ingestion gates remain open. |

Manual journey: sign in → project → Product Knowledge → reviewed/approved knowledge
→ story/acceptance criteria → analyze and resolve blockers → request distinct scenario
coverage → approve scenario → generate detailed cases → review/save/approve NLP design
→ export for manual use. Teach-back remains optional planned work. Avoid customer
credentials or personal data in training/design content.

See [PRODUCT_KNOWLEDGE](PRODUCT_KNOWLEDGE.md), [PLATFORM_PROMPTS](PLATFORM_PROMPTS.md)
and [UI_UX_REFRESH](UI_UX_REFRESH.md) for actual checks and limits. Phase 2 execution
architecture is planned in [HYBRID_EXECUTION_PLAN](HYBRID_EXECUTION_PLAN.md); it is not
implicitly authorized by Test Design completion work.
