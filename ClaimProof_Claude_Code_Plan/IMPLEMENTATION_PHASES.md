# 3-Hour Implementation Plan

## Strategy

Build one end-to-end vertical slice early. Do not build all backend
modules first and leave the UI until the end. Every phase must leave the
app runnable.

## Phase 0 --- Repository and contract lock (Hour 0--2)

**Tasks** - Inspect repository and existing code. - Create
frontend/backend skeleton and environment examples. - Confirm Python and
Node versions. - Add `.gitignore`, basic README run commands, and health
endpoint. - Add the enums and core Pydantic schemas from
`DATA_MODELS.md`.

**Acceptance** - Backend starts. - Frontend starts. - `GET /health`
succeeds. - No secrets committed.

## Phase 1 --- Persistence and synthetic seed data (Hour 2--6)

**Tasks** - Configure SQLite and ORM. - Create core tables: Claim,
Policy, Evidence, ExtractedFact, Evaluation, Finding, ReviewerDecision,
UploadRequest, AuditEvent. - Seed 3--5 synthetic policies and 4 demo
claims. - Add list/detail/create claim endpoints. - Add basic claims
queue UI.

**Acceptance** - Seed is idempotent. - Claims appear in UI. - Create and
detail flows work. - Policy versions are stable and synthetic.

## Phase 2 --- Safe uploads and extraction (Hour 6--12)

**Tasks** - Implement file validation and generated storage keys. -
Store original files outside frontend public directories. - Add PDF text
extraction using `pypdf` and TXT extraction. - Add OCR adapter
interface; implement only if time permits. - Persist evidence and
extraction status. - Extract common labels and values using
deterministic parsers: purchase date, serial/IMEI, model, amount,
currency, repair date. - Store source page/snippet and raw values.

**Acceptance** - PDF/TXT upload works. - Unsupported, oversized, corrupt
files return safe errors. - Failed extraction is visible and does not
reject a claim. - Facts link back to evidence.

## Phase 3 --- Deterministic rules and evaluation (Hour 12--18)

**Tasks** - Implement required-evidence, policy-match, coverage-window,
event-coverage, identifier/model/date/amount mismatch rules. - Implement
recommendation precedence from `DECISION_ENGINE.md`. - Persist a new
evaluation on every run. - Add source-linked findings to the API and
UI. - Add rule unit tests before adding AI summaries.

**Acceptance** - Same inputs produce the same rule results. - At least
one pass, missing-evidence, contradiction, and excluded-event scenario
work. - Every material finding has evidence references or explicitly
says source is unavailable. - No AI call required.

## Phase 4 --- AI provider abstraction (Hour 18--22)

**Tasks** - Define provider protocol. - Implement deterministic mock
provider first. - Add Sonnet adapter behind explicit config and
environment variable. - Validate provider outputs with Pydantic. - Use
AI only to summarize facts/findings; do not let it set recommendation or
mutate rule outcomes. - Implement safe fallback to deterministic
summary.

**Acceptance** - App works with no key. - Invalid AI JSON falls back
safely. - AI outage never becomes rejection. - Provider mode is visible
to the reviewer or in diagnostics.

## Phase 5 --- Reviewer decisions and customer upload link (Hour 22--30)

**Tasks** - Implement decision endpoint and UI controls. - Record reason
for rejection/override. - Implement scoped, random, expiring upload
tokens; store token hash only. - Build lightweight customer upload page
and public token-scoped endpoints. - Append resubmitted evidence without
overwriting older files. - Trigger re-evaluation after upload.

**Acceptance** - Reviewer can request information and receive a link. -
Valid token uploads evidence only to the intended claim. -
Expired/revoked/invalid tokens fail. - Customer endpoint cannot view
reviewer findings or other claims. - Audit trail records each step.

## Phase 6 --- UI polish and complete demo (Hour 30--38)

**Tasks** - Improve queue filters and status badges. - Add claim
timeline. - Add evidence/finding side-by-side layout. - Show rule ID,
severity, explanation, source document/page, and next action. - Add
empty, loading, and error states. - Make seeded demo claims one-click
accessible.

**Acceptance** - Reviewer can understand the case without reading raw
logs. - Every recommendation has clear reasons. - Demo is navigable
without manual database edits.

## Phase 7 --- Hardening, testing, and presentation (Hour 38--46)

**Tasks** - Run backend tests and frontend checks. - Test malformed and
oversized uploads. - Test token expiry/scope and reviewer overrides. -
Test missing AI credentials and simulated provider failure. - Fix
highest-impact bugs only. - Prepare demo script and known-limitations
slide.

**Acceptance** - All critical tests pass. - Fresh clone setup works from
README. - Demo scenarios match `DEMO_DATA.md`. - No fake claims of
production fraud detection.

## Phase 8 --- Buffer and final verification (Hour 46--48)

**Tasks** - Freeze features. - Run the demo from a clean database. -
Verify all four core scenarios. - Check environment variables and
startup instructions. - Prepare a short architecture explanation.

**Do not add new features in the final two hours unless they fix a
demo-blocking bug.**

## Cut line if behind schedule

Keep in this order: 1. Queue/detail UI 2. Upload and text extraction 3.
Deterministic rules and source-linked findings 4. Reviewer actions and
audit log 5. Synthetic policies/demo data 6. Customer upload-link flow
7. Mock AI summary 8. Sonnet adapter 9. OCR for scanned files and
cosmetic polish

If time runs out, a tested deterministic system with mock AI is better
than a broken Sonnet integration. Never fake an AI response and present
it as a real model result.
