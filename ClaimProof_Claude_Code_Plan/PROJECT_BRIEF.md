# Project Brief

## 1. Product

**ClaimProof** is a single reviewer workspace for evidence-based
verification of electronic-device warranty and insurance claims.

## 2. Supported scope

### Products

-   Laptop
-   Mobile phone

### Claim types

-   Warranty
-   Insurance

### MVP evidence types

-   Claim form/details
-   Purchase invoice or receipt
-   Warranty/insurance policy (for MVP, policy rules are selected from
    synthetic seeded policies)
-   Repair/service receipt
-   Damage description or customer statement as text
-   Optional supporting document

Photo-based damage interpretation, real insurer integrations, external
serial-number checks, and automated fraud verdicts are out of scope.

## 3. Primary user

An insurance/warranty reviewer who sees all submitted claims in a queue,
opens a case, inspects extracted evidence and rules, and records an
action.

A separate lightweight customer upload page is allowed only for
supplying requested additional documents. It is not a customer account
portal.

## 4. Core workflow

1.  Reviewer opens the queue or creates a demo claim.
2.  Reviewer selects product, claim type, and synthetic policy.
3.  Documents are uploaded and stored safely.
4.  The document pipeline extracts text and normalized facts with source
    locations.
5.  Deterministic checks evaluate required evidence, dates, product
    identifiers, policy coverage, exclusions, and claim amounts where
    applicable.
6.  The AI layer may produce a concise explanation from extracted facts
    and findings.
7.  The UI presents a recommendation, rule outcomes, source-linked
    findings, and missing evidence.
8.  Reviewer records a decision or requests additional information.
9.  If more information is requested, the backend issues a scoped,
    expiring upload link.
10. New evidence is appended as a new version; the claim is reprocessed
    and the audit history remains intact.

## 5. Recommendation statuses

Use these distinct values: - `RECOMMENDED_APPROVAL` -
`RECOMMENDED_REJECTION` - `MORE_INFORMATION_REQUIRED` -
`HUMAN_REVIEW_REQUIRED` - `PROCESSING` - `PROCESSING_FAILED`

The reviewer's actual action is stored separately: - `APPROVE` -
`REJECT` - `REQUEST_INFORMATION` - `ESCALATE` - `MARK_UNDER_REVIEW`

Do not conflate a recommendation with a human decision.

## 6. Functional requirements

-   List, search, and filter claims by status, product, claim type, and
    submission date.
-   Create a claim and upload one or more allowed document types.
-   Preserve the original uploaded file and metadata.
-   Extract text from digital PDFs and text-based files; support OCR
    behind a replaceable adapter if time allows.
-   Normalize core entities: product type/model, serial or IMEI when
    present, purchase date, incident date, claim date, repair date,
    claimed amount, currency, damage/failure description, and policy
    identifier.
-   Show extracted facts with source document, page number if available,
    and confidence.
-   Run deterministic policy and consistency rules.
-   Show each finding with severity, rule ID, explanation, source
    references, and next action.
-   Produce a recommendation with reasons and unresolved uncertainties.
-   Let reviewers record decisions and overrides with reasons.
-   Generate a customer upload link for missing evidence; allow safe
    upload without reviewer access.
-   Maintain append-only audit events for uploads, evaluations,
    recommendations, reviewer actions, and resubmissions.
-   Include synthetic seed data and a reliable end-to-end demo.

## 7. Non-functional requirements

-   Local setup should take no more than a few documented commands.
-   No AI key is required for the app to start or for tests to pass.
-   Core rules must be deterministic and tested.
-   Every claim must remain reviewable if AI is unavailable.
-   Handle malformed, oversized, unsupported, or unreadable files
    gracefully.
-   No claim should be rejected solely because extraction or a model
    failed.
-   Keep personal data synthetic for the demo.
-   Ensure customer upload tokens cannot read other claims or reviewer
    data.

## 8. Non-goals for the 3-hour MVP

-   Real-world policy/legal interpretation across arbitrary insurers.
-   Direct integration with insurance company systems.
-   Autonomous payment or settlement.
-   Automated fraud determination.
-   Photo-forensics or image manipulation detection.
-   Customer login, profile management, or a full customer portal.
-   Production multi-tenant security certification.
-   Distributed services, vector search, multi-agent frameworks, or
    complex workflow engines.

## 9. Success criteria

A reviewer can complete the seeded demo from claim queue to evidence
review to recommendation and final reviewer action. The system explains
at least one consistent claim, one missing-evidence claim, one
policy-ineligible claim, and one contradictory claim with traceable
evidence. The app runs with mock AI and remains usable if Sonnet is not
configured.
