# Architecture

## 1. Design principle

Use a **modular monolith**: one React frontend, one FastAPI backend, one
SQLite database, and local file storage. Keep AI and OCR behind
adapters. The architecture must be useful even when no AI provider is
configured.

## 2. Component map

### Frontend

-   `ClaimsQueue`: table, filters, search, status badges.
-   `ClaimDetail`: overview and timeline.
-   `EvidencePanel`: original document metadata and extracted facts.
-   `FindingsPanel`: contradictions, missing evidence, rule outcomes,
    source links.
-   `DecisionPanel`: recommendation, reviewer action, override reason.
-   `CustomerUploadPage`: token-scoped upload form only.
-   Shared API client with typed response shapes and clear loading/error
    states.

### Backend modules

-   `api/`: routes, dependency injection, request/response models.
-   `claims/`: claim lifecycle and orchestration.
-   `documents/`: upload validation, storage, extraction adapters,
    source locations.
-   `normalization/`: normalized facts and identifier/date/money
    parsing.
-   `policies/`: synthetic policy definitions and policy lookup.
-   `rules/`: pure deterministic rules and finding aggregation.
-   `review/`: recommendation generation and AI summary orchestration.
-   `ai/`: provider protocol, mock provider, Sonnet provider, output
    validation.
-   `audit/`: append-only audit events.
-   `uploads/`: customer upload-token creation and validation.
-   `db/`: models, session, migrations or create-all for MVP.

### Persistence

SQLite stores claims, evidence metadata, extracted facts, findings,
evaluations, reviewer decisions, upload requests/tokens, and audit
events. Original files live in a dedicated local storage directory
outside public frontend assets. Store only generated server-side paths
in the database.

## 3. Suggested repository structure

``` text
claimproof/
  CLAUDE.md
  README.md
  docs/
    PROJECT_BRIEF.md
    ARCHITECTURE.md
    DATA_MODELS.md
    DECISION_ENGINE.md
    API_CONTRACTS.md
    IMPLEMENTATION_PHASES.md
    TESTING.md
    DEMO_DATA.md
  backend/
    app/
      main.py
      config.py
      api/
      db/
      claims/
      documents/
      normalization/
      policies/
      rules/
      review/
      ai/
      audit/
      uploads/
    tests/
    pyproject.toml or requirements.txt
    .env.example
  frontend/
    src/
      api/
      components/
      pages/
      types/
    package.json
  storage/
    .gitkeep
  .gitignore
```

Do not create every folder as empty scaffolding up front. Create modules
as the related phase starts.

## 4. Document pipeline

1.  Validate extension, MIME type, file size, and file signature where
    feasible.
2.  Store with a generated UUID filename; preserve the original filename
    only as metadata.
3.  Create an evidence record before extraction so failed extraction is
    visible.
4.  Extract text:
    -   Digital PDF: `pypdf`
    -   Plain text: safe UTF-8 decoding
    -   Scanned PDF/image: OCR adapter (optional in MVP; Tesseract or
        PaddleOCR)
5.  Persist extracted text or a bounded excerpt plus page/field source
    locations.
6.  Normalize facts into typed records with confidence and evidence
    references.
7.  Run deterministic rules on normalized facts.
8.  Optionally ask the configured AI provider to summarize extracted
    facts and findings.
9.  Validate AI output and persist it separately from rule results.
10. Aggregate recommendation using deterministic precedence.

Do not pass the raw uploaded file to the LLM by default. Prefer passing
only the minimum extracted text and already-known findings. If provider
configuration is absent, the mock provider must return a clear,
non-fabricated summary or the UI can use deterministic templates.

## 5. Hybrid runtime AI

Configuration: - `AI_PROVIDER=mock` by default. - `AI_PROVIDER=sonnet`
only when explicitly set and credentials are configured. -
`ANTHROPIC_API_KEY` is read from environment; never committed. -
`AI_ENABLED` may be used as a separate kill switch.

Interface: -
`extract_facts(document_text, metadata) -> validated facts` -
`summarize_review(claim, facts, findings) -> validated summary`

Keep extraction deterministic where possible using regex/date/amount
parsing and known form labels. AI extraction is a fallback for ambiguous
unstructured text, not the only path.

AI output must use a strict schema and be treated as untrusted. Any fact
that lacks a valid source reference is either rejected or marked
unsupported. AI cannot alter `rule_results`, the selected policy, or
reviewer decisions.

## 6. Recommendation aggregator

The rule engine returns: - `rule_results` - `findings` -
`missing_evidence` - `blocking_conditions` - `indeterminate_conditions`

The aggregator applies documented precedence in `DECISION_ENGINE.md`.
Processing failure is a technical state, not a rejection. A known
mandatory exclusion may recommend rejection only when the relevant facts
and policy clause are established. Missing evidence or material
ambiguity should normally request information or human review.

## 7. Security and reliability

-   Limit upload size (default 10 MB per file; configure centrally).
-   Allow only PDF, PNG, JPEG, and TXT in MVP.
-   Generate storage filenames; prevent path traversal.
-   Do not serve storage files as static public assets.
-   Validate upload token hash, expiry, revocation, claim scope, and
    allowed file count.
-   Avoid logging extracted sensitive text or tokens.
-   Use transaction boundaries for reviewer decisions and audit events.
-   Add indexes for claim status, created date, claim ID, and
    upload-token hash.
-   Use UTC timestamps.
-   Add a health endpoint that does not reveal secrets.
-   Keep CORS restricted to the configured local frontend origin.

## 8. Implementation status (kept current -- see PROGRESS.md and DECISIONS.md)

Built as specified, with these concrete choices:
- Backend `backend/app/`: `api/` (routes, schemas, serializers), `claims/service.py` (create, ingest, evaluate,
  decisions), `documents/` (storage validation, extract: TXT/pypdf/Tesseract), `normalization/parsers.py`
  (label-based parsers), `rules/engine.py` (22 pure rules) + `rules/aggregator.py` (precedence), `ai/provider.py`
  (mock + Sonnet, schema-validated, summary only), `uploads/tokens.py`, `audit/`, `demo/` (fixtures + seed), `db/`.
- Frontend `frontend/src/`: pages `ClaimsQueue`, `NewClaim`, `ClaimDetailPage` (evidence, findings, decision,
  timeline, upload links), `CustomerUpload` (token page, uses only `/public/*` with `X-Upload-Token`).
- Evidence flow: validate -> store under UUID key -> Evidence row -> extract -> facts (with snippet/page/confidence)
  -> evaluate -> Findings + Evaluation (append-only) -> audit event.
- Public endpoints use header `X-Upload-Token` (not the URL path) so access logs never contain tokens.
- Demo seed: `POST /api/v1/demo/seed` or `python -m app.demo.seed`.

### Frontend structure (UX v2)
`src/pages/` ClaimsQueue, NewClaim (wizard), ClaimDetailPage (container), CustomerUpload; `src/claim/` ResultCard,
DecisionDialog, FindingsTab, DocumentsTab, OtherTabs (details + history); `src/components/ui.tsx` shared primitives
(Badge, Card, Stepper, Tabs, Modal); `src/constants.ts` event options + document slots; `src/api.ts` client + wording.
