# Branch workflow

Accepted 2026-11-11: use `dev` as the single ongoing development branch. Before any merge into `main`, create a pull request from `dev` to `main` for review. Merge only after user approval; do not merge or push changes directly to `main`. Do not create extra feature branches unless explicitly requested. Vercel production should follow `main`. Historical feature branches are already merged.

## Consolidation verification

TypeScript passed after merge. Six focused UI proxy/preparation/startup tests passed. Changed-file credential-pattern and Git whitespace checks passed. The API visual specification unittest stalled without output and was interrupted; it did not pass. Production deployment, real login, provider calls and browser execution were not verified by this consolidation.
