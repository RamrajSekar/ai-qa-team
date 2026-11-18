# Overview pending reviews

2026-11-18: read-only project queue for Story, Scenario, Test Case and Knowledge.
Review links open existing item review/approval flows. No inline/bulk approval,
analysis, generation, extraction or execution is triggered by viewing the table.
After approval, returning to Overview or Refresh reviews reloads canonical state.

The queue uses story approval summaries (including manual receipts), scenario
approval/context validity, TestDesignReview state, active training reviews with
receipt-resolved saved versions, and submitted/pending story knowledge changes.
Discarded training and approved knowledge history are excluded. Historical orphan
drafts outside active UI training/change reviews are not promoted into new work.
Blocked/stale items remain visible with their reason and original review link.

Pending with lists eligible real users, not an invented personal assignment.
Story and knowledge use project ADMINs; scenarios use the creator under existing
API policy; cases use project members unless test_design_admin_review requires
ADMIN. Names come only from active project membership and same-account active
profiles, never platform roles or unrelated customer users. Missing eligible
reviewers are explicit. No assignment/notification feature is introduced.

Each page scans up to 20 records per source type (API maximum 50); Next reviews
continues the scan even if a page contains only already-approved records. This is
not a claim of a project-wide total. Source reads are project-scoped, bounded and
hydration concurrency is four. A failed type is marked unavailable without
turning it into an empty queue. The table loads independently from Overview
summaries, with private/no-store API responses and an explicit refresh action.

No migration or new flags. Existing feature gates and per-item authorization
remain authoritative. A deep-linked scenario/case outside the current catalog
page is loaded through its existing authorized read endpoint and its project is
checked again before opening. Navigation does not approve any item.


Verification: five isolated backend checks cover all item types, canonical manual
approval removal, same-account reviewer names/role policy, read-only behavior,
feature gates, pagination, partial failures and authorized private responses.
Browser catalog/navigation regressions and queue review/refresh checks passed;
off-page review links verify the returned project before opening an item.
TypeScript/scoped ESLint and whitespace checks passed. No live Mongo load,
real production latency, provider calls or browser execution were used.
