# Testing and Acceptance Criteria

## 1. Backend unit tests

### Rules

-   Correct product and claim type passes policy matching.
-   Wrong product/claim type returns the expected rule failure.
-   Coverage date inside policy window passes.
-   Coverage date outside policy window produces the configured
    rejection candidate only when dates are reliable.
-   Missing required invoice yields `MORE_INFORMATION_REQUIRED`, not
    rejection.
-   Serial/IMEI mismatch produces a finding with both source facts.
-   Repair date before incident date flags a contradiction, not fraud.
-   Amount mismatch is flagged without silently replacing either amount.
-   Low-confidence material fact produces `INDETERMINATE`.
-   AI unavailable does not change rule results or recommendation except
    to indicate degraded summary mode.
-   Repeated evaluation creates a new evaluation and preserves the old
    one.

### Upload security

-   Reject unsupported extensions and MIME types.
-   Reject files over configured size.
-   Generate storage keys independent of the original filename.
-   Reject traversal-like filenames and never use them as paths.
-   Expired, revoked, unknown, or exhausted upload tokens fail.
-   Token can upload only to its associated claim.
-   Customer endpoint does not return internal findings or reviewer
    notes.
-   Raw tokens are not stored in the database or logs.

### Reviewer decisions and audit

-   Rejection requires a reason.
-   Recommendation override requires a reason.
-   Request-information action requires at least one item.
-   Each reviewer action appends an audit event.
-   Audit endpoint does not expose secrets or raw evidence contents.

## 2. API integration tests

-   Create claim → upload invoice → evaluate → view findings.
-   Request more information → receive link → upload new evidence →
    re-evaluate.
-   Unsupported file returns `415`; oversized file returns `413`.
-   Unknown claim/evidence returns `404`.
-   Invalid request body returns `422`.
-   No AI key configured still allows full workflow.
-   Provider returns malformed JSON; deterministic summary fallback is
    used.

## 3. Frontend checks

-   Queue loads and displays empty/error/loading states.
-   Filters change results.
-   Claim detail shows status, evidence, findings, and recommendation.
-   Source evidence can be opened without exposing local filesystem
    paths.
-   Reviewer cannot submit an invalid action.
-   Customer upload page displays only requested items and upload
    status.
-   A failed upload shows an actionable error.
-   Long findings and source snippets remain readable.

## 4. End-to-end acceptance tests

### Scenario A --- Consistent eligible claim

Expected: `RECOMMENDED_APPROVAL`; no blocking finding; evidence links
present.

### Scenario B --- Missing purchase proof

Expected: `MORE_INFORMATION_REQUIRED`; explicit requested document; no
rejection.

### Scenario C --- Explicit excluded event

Expected: `RECOMMENDED_REJECTION` only if the event and policy exclusion
are reliably established; reason cites the synthetic policy rule.

### Scenario D --- Contradictory repair/incident dates

Expected: `HUMAN_REVIEW_REQUIRED` or `MORE_INFORMATION_REQUIRED`
according to materiality; no fraud verdict.

### Scenario E --- AI provider unavailable

Expected: rule results remain unchanged; deterministic summary shown; no
rejection due to provider failure.

### Scenario F --- Customer resubmission

Expected: new evidence version; old evidence remains; new evaluation is
created; audit history shows request and upload.

## 5. Test execution

Document exact commands in the repository README. Suggested commands: -
Backend: `pytest -q` - Frontend: `npm run test` if configured - Frontend
type check/build: `npm run build` - API smoke test: documented `curl`
calls or a small integration script

Do not report tests as passing unless they were actually run.
