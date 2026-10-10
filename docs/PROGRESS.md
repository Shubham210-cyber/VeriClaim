# PROGRESS (handoff log -- update after every phase)

If context is lost: read CLAUDE.md, DECISIONS.md, this file, then continue
with the first unchecked phase.

Env: Windows, Python 3.13 (`py -3.13`; 3.14 lacks some wheels), Node 24,
Tesseract at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
Repo: https://github.com/Shubham210-cyber/VeriClaim (branch `main`).
Code layout: `backend/` (FastAPI), `frontend/` (Vite React TS), `docs/`,
`scripts/`, `storage/`.

## Status
- [x] Plan reviewed; conflicts resolved in DECISIONS.md
- [x] Phase 0 skeleton
- [x] Phase 1 backend (frontend UI pending)
- [x] Phase 2 uploads + extraction (TXT/PDF/OCR)
- [x] Phase 3 rules + evaluation (22 rules)
- [x] Phase 4 AI provider (mock+sonnet, untested live)
- [x] Phase 5 BACKEND decisions + customer upload (UI pending)
- [ ] Phase 6 polish
- [ ] Phase 7 hardening + README

## Log
- Repo linked to GitHub; docs moved to `docs/`.

- Backend complete: `backend/app/*`, 40 pytest pass (`cd backend; .\.venv\Scripts\python -m pytest -q`). Run API: `.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Seed: `python -m app.demo.seed` or `POST /api/v1/demo/seed`.
- NOTE: SQLAlchemy pinned to 2.0.x: Windows Application Control blocks the 2.1 compiled module (2.0 falls back to pure Python). Do not upgrade.
- Demo OCR verified: CP-DEMO-001..004 -> APPROVAL / MORE_INFO / REJECTION / HUMAN_REVIEW with real Tesseract.
- NEXT: frontend (queue, detail, evidence, findings, decision panel, customer upload page, seed button), README, then final verification.
- GitHub push blocked: saved git credential (NiranjanSathishkumar) has no write access to Shubham210-cyber/VeriClaim (HTTP 403). Commits are local until access is fixed.
