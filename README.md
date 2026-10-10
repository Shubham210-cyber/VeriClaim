# VeriClaim (ClaimProof)

Evidence-based **reviewer decision support** for laptop and mobile-phone warranty/insurance claims.
Deterministic rules decide eligibility checks; AI (optional) only summarizes. Nothing here is a real
insurance decision: **all data and policies are synthetic, and all demo documents are stamped
"FAKE - SYNTHETIC DEMO DOCUMENT".**

Docs: [`docs/DECISIONS.md`](docs/DECISIONS.md) (authoritative decisions), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
[`docs/PROGRESS.md`](docs/PROGRESS.md) (handoff log).

## Run it (Windows)

Prereqs: Python 3.13, Node 20+, [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
(`winget install UB-Mannheim.TesseractOCR`; needed for image documents).

```powershell
# backend (terminal 1)
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# frontend (terminal 2)
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Open http://localhost:5173 and click **Add sample claims** (creates 4 synthetic claims by running the real
upload/OCR/rules pipeline). No API key is needed; `AI_PROVIDER=mock` is the default.

| Demo claim | Scenario | Expected recommendation |
|---|---|---|
| CP-DEMO-001 | Consistent warranty claim | RECOMMENDED_APPROVAL |
| CP-DEMO-002 | No purchase invoice | MORE_INFORMATION_REQUIRED |
| CP-DEMO-003 | Accidental damage under warranty (explicit exclusion) | RECOMMENDED_REJECTION |
| CP-DEMO-004 | Repair receipt predates reported incident | HUMAN_REVIEW_REQUIRED |

Try the customer flow: open CP-DEMO-002 -> Your decision -> *Ask customer for more information* -> copy the link,
open it in a private window, upload one of the images in `demo_fixtures/`, then reload the claim.

## Tests

```powershell
cd backend; .\.venv\Scripts\python -m pytest -q     # rules, API, security, AI-failure, real OCR demo
cd frontend; npm run build                          # type-check + production build
```

## Configuration (environment variables)

| Var | Default | Notes |
|---|---|---|
| `AI_PROVIDER` | `mock` | `sonnet` needs `ANTHROPIC_API_KEY`; falls back to the deterministic summary on any failure |
| `AI_ENABLED` | `true` | kill switch |
| `AI_MODEL` | `claude-sonnet-5-5` | |
| `TESSERACT_CMD` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | |
| `MAX_UPLOAD_BYTES` | 10 MB | |
| `DATABASE_URL`, `STORAGE_DIR`, `CONFIDENCE_THRESHOLD`, `FRONTEND_ORIGIN` | see `backend/app/config.py` | |

## Known limitations (honest list)

- No reviewer authentication: local demo only, backend binds to 127.0.0.1.
- OCR only for PNG/JPEG; scanned PDFs (no text layer) are reported as unreadable, not rejected.
- Extraction handles labelled fields, marketplace-style invoices (dates, line-item table, amount in words) and claim-hinted verification; truly free-form documents are not understood.
- The Sonnet adapter is implemented but was not exercised against the live API in development.
- The event type is classified by the reviewer, not inferred from text.
- No frontend unit tests; the UI is type-checked, built and visually checked with headless-browser screenshots only.
- OCR can misread currency symbols and separators on low-resolution scans; the amount in words is used as a cross-check.
- Not a fraud detector: discrepancies are reported neutrally as "needs clarification".
- SQLAlchemy is pinned to 2.0.x (a Windows Application Control policy blocked the 2.1 compiled module).

