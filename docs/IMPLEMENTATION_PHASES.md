# 3-Hour Implementation Plan (replaces the old 48-hour table)

Read `DECISIONS.md` first; it overrides other docs. Track status in
`PROGRESS.md` (update after every phase, commit + push).

Every phase leaves the app runnable and ends with a commit + `git push`.

| Phase | Time | Content |
|---|---|---|
| 0 | 0:00-0:15 | Skeleton: FastAPI, Vite React TS, `.gitignore`, `/health`, enums, config |
| 1 | 0:15-0:40 | SQLAlchemy models, seed (4 policies, 4 demo claims + fixtures), claims list/detail/create API, queue UI |
| 2 | 0:40-1:10 | Upload validation, storage, PDF/TXT/OCR extraction, regex fact parsers, claim-record facts |
| 3 | 1:10-1:50 | Rule engine, aggregator, evaluation API + pytest for 4 scenarios, findings UI |
| 4 | 1:50-2:05 | AI provider (mock + sonnet), fallback, provider mode shown |
| 5 | 2:05-2:35 | Decisions API/UI, audit, upload-request token flow, customer page, re-evaluation |
| 6 | 2:35-2:55 | UI polish: filters, timeline, states, synthetic-data banner |
| 7 | 2:55-3:00 | README, final pytest/build run, PROGRESS.md |

## Cut line (if behind)
1. Queue/detail UI 2. Upload + extraction 3. Rules + findings 4. Decisions +
audit 5. Seeds 6. Customer link 7. Mock AI 8. Sonnet adapter 9. Polish.
A tested deterministic system with mock AI beats a broken Sonnet adapter.

Acceptance criteria per phase are in `TESTING.md`. Do not claim tests pass
unless run.
