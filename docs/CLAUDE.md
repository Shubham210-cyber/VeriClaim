# CLAUDE.md --- ClaimProof Development Rules

## Mission

Build ClaimProof, a hackathon MVP for evidence-based review of warranty
and insurance claims for laptops and mobile phones. The
reviewer is the primary user. The application extracts facts from
uploaded documents, compares them against synthetic policy rules, flags
missing evidence and contradictions, and produces an explainable
recommendation.

## Before every implementation task

0.  Read `docs/DECISIONS.md` (overrides other docs) and `docs/PROGRESS.md`
    (current status). After each phase update PROGRESS.md, commit, and
    `git push origin main`.
1.  Read `README.md`, `PROJECT_BRIEF.md`, and the relevant
    architecture/data/rules/API document.
2.  Inspect the current repository before editing. Do not assume files
    or dependencies exist.
3.  State a short plan, then implement the smallest complete vertical
    slice.
4.  Run relevant tests and lint/type checks. Fix failures before moving
    on.
5.  Summarize changed files, tests run, known limitations, and the next
    step.

## Non-negotiable constraints

-   Keep the architecture a **modular monolith**. Do not add
    microservices, queues, vector databases, or multi-agent frameworks.
-   Use deterministic Python rules for dates, coverage windows, required
    fields, policy exclusions, limits, and identifier comparisons.
-   AI output is untrusted input. Validate it against Pydantic schemas
    before use.
-   The AI must not make the final decision, create policy terms, change
    rule outcomes, or label a customer as fraudulent.
-   A discrepancy is not proof of fraud. Use neutral language:
    `inconsistency`, `unverified`, `needs clarification`, or
    `risk indicator`.
-   Every material finding must cite a source document and a
    page/field/snippet when available. If source location is
    unavailable, say so explicitly.
-   Do not invent evidence or source references. Never create a citation
    that points to a location not actually extracted.
-   If OCR confidence is low or required evidence cannot be parsed, mark
    it as `UNKNOWN`/`INDETERMINATE`; do not guess.
-   Technical errors must never become claim rejections.
-   Preserve original uploads. New uploads create new evidence versions;
    do not overwrite previous evidence.
-   Reviewer overrides require a reason and must be written to the audit
    log.
-   Do not store secrets in source control. Read API credentials from
    environment variables.
-   Restrict uploads by extension, MIME type, size, and generated
    storage name. Never trust user-provided paths.
-   Do not send document contents to an external AI provider unless the
    provider is configured and the code path clearly permits it.
-   Keep customer upload links random, revocable, scoped to one claim,
    and expiring. Never expose the reviewer dashboard through a customer
    token.
-   Use synthetic people, device identifiers, invoices, policies, and
    claim data in demos.

## Implementation style

-   Prefer simple, typed, explicit code over abstractions designed for
    hypothetical future needs.
-   Keep modules small and responsibilities clear.
-   Use Pydantic models at API and AI boundaries.
-   Use UTC timestamps internally and ISO 8601 over APIs.
-   Use `Decimal` for money; do not use binary floating point for
    currency.
-   Use enums for lifecycle status, finding severity, rule result, claim
    type, and recommendation.
-   Keep business logic out of FastAPI route handlers and React
    components.
-   No magic strings for decision statuses or rule IDs.
-   Make rule evaluation deterministic and unit-testable without calling
    an LLM.
-   Add comments for non-obvious reasoning, not for obvious code.
-   Avoid broad exception swallowing. Return useful, non-sensitive
    errors and log stack traces server-side.
-   Do not claim a feature works unless it has been tested.

## AI provider contract

Implement one provider interface such as: - `extract_document(...)` -
`summarize_findings(...)`

Provider modes: 1. `mock`: deterministic fixture-based output, default
for tests and no credentials. 2. `sonnet`: enabled only when required
credentials and explicit configuration are present. 3. If Sonnet is
unavailable or errors, fall back to a clearly marked degraded/mock path
only where safe. Never fabricate extracted facts as if they came from a
document.

The core decision engine must work without AI. AI enriches the review;
it is not a dependency for applying known rules.

## Definition of done for each phase

-   Code follows the documented contracts.
-   Tests cover success and failure paths.
-   No unrelated refactors.
-   Frontend loading, empty, error, and success states exist for touched
    flows.
-   README instructions stay accurate.
-   Report blockers honestly instead of adding fake functionality.
