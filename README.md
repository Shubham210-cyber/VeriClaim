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

Open http://localhost:5173. To fill the queue with ten example claims (run through the real upload/OCR/rules
pipeline), run once from `backend/`:

```powershell
.\.venv\Scripts\python -m app.demo.seed
```

The app has no seeding button; the same thing is available as `POST /api/v1/demo/seed`. No API key is needed;
`AI_PROVIDER=mock` is the default.

| Example claim | Scenario | Recommendation | Queue state |
|---|---|---|---|
| CP-2026-1001 | Laptop warranty, everything consistent | Approve | Awaiting review |
| CP-2026-1002 | Laptop insurance, no purchase invoice | More information | Awaiting review |
| CP-2026-1003 | Accidental damage under a warranty (explicit exclusion) | Decline | Awaiting review |
| CP-2026-1004 | Repair receipt predates the reported incident | Human review | Awaiting review |
| CP-2026-1005 | Phone insurance, clean claim with payout estimate | Approve | Approved |
| CP-2026-1006 | Phone warranty, IMEI digits swapped vs the invoice | Human review | Awaiting review |
| CP-2026-1007 | Laptop warranty, incident 587 days after purchase | Decline | Awaiting review |
| CP-2026-1008 | Laptop insurance, claim above the maximum payable | Human review | Escalated |
| CP-2026-1009 | Phone insurance, purchase date printed `06/04/2026` (never guessed) | More information | Awaiting review |
| CP-2026-1010 | Phone insurance, repair done but receipt missing | More information | Waiting for customer |

The invoices are generated, realistic shop-style documents (GST table, IMEI line, amount in words, Indian number
formatting), all stamped FAKE; `demo_fixtures/` is regenerated automatically when its version changes.

## How the app flows

1. **New claim** is a 3-step wizard: choose the cover, enter device and incident details, add the documents.
   Required documents are flagged. On "Create claim" the documents are read and the claim is reviewed automatically.
2. The **claim page** shows a progress bar (Add documents, Review, Your decision) and a recommendation card with the
   decision buttons right there: *Approve*, *Decline*, *Ask customer for info* (and *More*: escalate / mark under review).
   The recommended action is highlighted. Reasons are required for declines and for decisions that differ from the
   recommendation.
3. Tabs below hold the detail: **What we found** (issues first, each linked to its source document), **Documents**
   (upload slots per document, with what was read), **Claim details**, **History** (audit trail and upload links).
4. Uploading a new document on the claim page re-runs the review automatically.
5. **Decision pack** (button on the recommendation card): an editable draft customer letter that follows the outcome
   (approval with an illustrative payout estimate, decline citing the exclusion and document, information request, or a
   neutral clarification), plus a printable one-page case file with findings, evidence, decision and history. Letters
   never contain internal codes or the word "fraud", and the reviewer's internal note stays in the case file only.
   Nothing is sent automatically; use Copy or Print / Save as PDF.

Try the customer flow: open CP-2026-1002 -> *Ask customer for info* -> *Create link* -> copy the link,
open it in a private window, send one of the images in `demo_fixtures/`, then reload the claim.

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

