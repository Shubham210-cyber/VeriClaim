# ClaimProof --- Claude Code Implementation Plan

A 3-hour hackathon MVP for evidence-based warranty and insurance claim
review for **laptops and mobile phones**.

## Start here

1.  Read `CLAUDE.md` before coding.
2.  Read `PROJECT_BRIEF.md` and `ARCHITECTURE.md`.
3.  Implement in the exact order in `IMPLEMENTATION_PHASES.md`.
4.  Treat `DECISION_ENGINE.md`, `DATA_MODELS.md`, and `API_CONTRACTS.md`
    as contracts. If an implementation choice conflicts with them,
    update the relevant document first.
5.  Use `TESTING.md` as the definition of done.

## Planning files

-   `CLAUDE.md` --- instructions for Claude Code/Sonnet, coding
    guardrails, workflow.
-   `PROJECT_BRIEF.md` --- scope, actors, requirements, explicit
    non-goals.
-   `ARCHITECTURE.md` --- component boundaries, runtime AI strategy,
    repository layout.
-   `DATA_MODELS.md` --- canonical entities, enums, persistence and
    audit rules.
-   `DECISION_ENGINE.md` --- deterministic rules, outcomes, conflict
    handling.
-   `API_CONTRACTS.md` --- endpoints and request/response shapes.
-   `IMPLEMENTATION_PHASES.md` --- strictly time-boxed 3-hour plan and
    priorities.
-   `TESTING.md` --- acceptance criteria, tests, demo scenarios.
-   `DEMO_DATA.md` --- synthetic policies, sample cases, and expected
    outcomes.

## Recommended stack

-   Frontend: React + TypeScript + Vite
-   Backend: Python + FastAPI + Pydantic
-   Persistence: SQLite + SQLAlchemy (or SQLModel, choose one and stay
    consistent)
-   Document extraction: `pypdf` for digital PDFs; Tesseract or
    PaddleOCR behind an adapter for scanned documents
-   AI: one provider interface with Sonnet adapter when configured and
    deterministic mock fallback
-   Tests: Pytest for backend; Vitest/React Testing Library if time
    permits

## 3-hour priority

Ship the reviewer queue, seeded cases, deterministic rules, evidence-linked findings, and reviewer action first. Customer upload links, OCR for arbitrary scans, and Sonnet runtime calls are stretch items.

## MVP principle

The product is **reviewer decision support**, not an autonomous fraud
judge. Rules determine objective eligibility checks. AI may extract,
summarize, and explain; it may not invent policy rules, override hard
rule results, or independently declare fraud.
