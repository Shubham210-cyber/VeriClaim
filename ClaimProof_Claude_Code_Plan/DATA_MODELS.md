# Data Models and Persistence Contract

Use Pydantic models at API boundaries and database models for
persistence. Avoid maintaining multiple competing definitions of the
same enum.

## 1. Enums

### ProductType

- `LAPTOP`
- `MOBILE_PHONE`

### ClaimType

-   `WARRANTY`
-   `INSURANCE`

### ClaimStatus

-   `SUBMITTED`
-   `PROCESSING`
-   `AWAITING_REVIEW`
-   `AWAITING_CUSTOMER`
-   `APPROVED`
-   `REJECTED`
-   `ESCALATED`
-   `CLOSED`
-   `PROCESSING_FAILED`

### Recommendation

-   `RECOMMENDED_APPROVAL`
-   `RECOMMENDED_REJECTION`
-   `MORE_INFORMATION_REQUIRED`
-   `HUMAN_REVIEW_REQUIRED`
-   `PROCESSING`
-   `PROCESSING_FAILED`

### ReviewerAction

-   `APPROVE`
-   `REJECT`
-   `REQUEST_INFORMATION`
-   `ESCALATE`
-   `MARK_UNDER_REVIEW`

### RuleResult

-   `PASS`
-   `FAIL`
-   `INDETERMINATE`
-   `NOT_APPLICABLE`

### Severity

-   `INFO`
-   `LOW`
-   `MEDIUM`
-   `HIGH`
-   `CRITICAL`

### EvidenceType

-   `CLAIM_FORM`
-   `PURCHASE_INVOICE`
-   `POLICY_DOCUMENT`
-   `WARRANTY_DOCUMENT`
-   `REPAIR_RECEIPT`
-   `CUSTOMER_STATEMENT`
-   `OTHER`

### ExtractionStatus

-   `PENDING`
-   `SUCCEEDED`
-   `PARTIAL`
-   `FAILED`

## 2. Core entities

### Claim

-   `id`: UUID string
-   `claim_number`: human-readable unique ID, e.g. `CP-2026-0001`
-   `product_type`: ProductType
-   `product_brand`: optional string
-   `product_model`: optional string
-   `device_identifier`: optional string; label the identifier type
    separately where known (serial/IMEI)
-   `claim_type`: ClaimType
-   `policy_id`: foreign key to Policy
-   `incident_date`: optional date
-   `submitted_at`: UTC datetime
-   `claimed_amount`: optional Decimal
-   `currency`: ISO currency code; synthetic demo default `INR`
-   `damage_or_failure_description`: optional string
-   `status`: ClaimStatus
-   `created_at`, `updated_at`: UTC datetime

### Policy

-   `id`: stable string such as `SYN-WAR-LAPTOP-01`
-   `name`: display name
-   `product_type`: ProductType
-   `claim_type`: ClaimType
-   `valid_from`, `valid_to`: optional dates for the policy/product plan
-   `coverage_days_from_purchase`: optional integer
-   `covered_event_types`: list of normalized event codes
-   `excluded_event_types`: list of normalized event codes
-   `max_claim_amount`: optional Decimal
-   `deductible_amount`: optional Decimal
-   `requires_purchase_proof`: bool
-   `requires_device_identifier`: bool
-   `required_evidence_types`: list of EvidenceType
-   `policy_version`: string
-   `source_label`: always `SYNTHETIC_DEMO_POLICY` for seeded MVP data

Keep policy schema explicit. Do not store free-form policy text as the
sole source of decision logic.

### Evidence

-   `id`: UUID string
-   `claim_id`: foreign key
-   `evidence_type`: EvidenceType
-   `original_filename`: sanitized display-only name
-   `storage_key`: generated server-side relative key
-   `mime_type`: validated MIME
-   `size_bytes`: integer
-   `sha256`: file hash for integrity and duplicate detection
-   `version_number`: integer per claim/evidence purpose
-   `uploaded_by`: `REVIEWER` or `CUSTOMER_LINK`
-   `uploaded_at`: UTC datetime
-   `extraction_status`: ExtractionStatus
-   `extraction_error_code`: optional safe error code

### ExtractedFact

-   `id`: UUID string
-   `claim_id`: foreign key
-   `evidence_id`: foreign key
-   `field_name`: stable field key such as `purchase_date`
-   `raw_value`: extracted original text
-   `normalized_value`: typed/string-normalized value
-   `confidence`: float from 0 to 1, nullable if unavailable
-   `source_page`: optional integer, 1-based
-   `source_snippet`: optional bounded text excerpt
-   `extraction_method`: `REGEX`, `OCR`, `AI`, or `MANUAL`
-   `created_at`: UTC datetime

A fact must reference the evidence it came from. Do not store ungrounded
AI claims as extracted facts.

### Finding

-   `id`: UUID string
-   `claim_id`: foreign key
-   `evaluation_id`: foreign key
-   `rule_id`: stable rule identifier
-   `severity`: Severity
-   `result`: RuleResult
-   `title`: concise label
-   `explanation`: neutral explanation
-   `field_name`: optional normalized field involved
-   `evidence_ids`: list of related evidence IDs
-   `source_fact_ids`: list of facts supporting the finding
-   `recommended_action`: optional string
-   `created_at`: UTC datetime

### Evaluation

-   `id`: UUID string
-   `claim_id`: foreign key
-   `policy_id`: foreign key
-   `rules_version`: string
-   `recommendation`: Recommendation
-   `reason_codes`: list of stable codes
-   `summary`: deterministic summary
-   `ai_summary`: optional separately stored validated AI summary
-   `ai_provider`: `mock`, `sonnet`, or `none`
-   `started_at`, `completed_at`: UTC datetimes
-   `processing_error_code`: optional safe code

Every re-evaluation creates a new Evaluation. Do not mutate the prior
evaluation to hide history.

### ReviewerDecision

-   `id`: UUID string
-   `claim_id`: foreign key
-   `evaluation_id`: foreign key
-   `action`: ReviewerAction
-   `reason`: required for overrides and rejection; recommended for all
    actions
-   `requested_evidence`: list of EvidenceType or structured field
    requests
-   `reviewer_label`: optional demo label (no authentication implied)
-   `created_at`: UTC datetime

### UploadRequest

-   `id`: UUID string
-   `claim_id`: foreign key
-   `token_hash`: hash of random token; never store raw token
-   `requested_items`: structured list of missing
    evidence/clarifications
-   `expires_at`: UTC datetime
-   `revoked_at`: optional UTC datetime
-   `max_uploads`: integer
-   `upload_count`: integer
-   `created_at`: UTC datetime

Only return the raw token once, when creating the link. The public route
may upload evidence to its scoped claim but cannot list claims or read
reviewer findings.

### AuditEvent

-   `id`: UUID string
-   `claim_id`: foreign key
-   `event_type`: stable string/enum
-   `actor_type`: `SYSTEM`, `REVIEWER`, `CUSTOMER_LINK`
-   `actor_label`: optional
-   `details_json`: structured non-secret details
-   `created_at`: UTC datetime

Append-only. Never store raw upload tokens or API secrets in audit
details.

## 3. Money, dates, and identifiers

-   Money uses Decimal and explicit currency.
-   Dates use ISO `YYYY-MM-DD`; datetimes use UTC ISO 8601.
-   Preserve raw identifier text and normalize only safe formatting
    characters. Do not silently change characters that could distinguish
    serial numbers.
-   Do not compare identifiers when either value is low-confidence; emit
    `INDETERMINATE`.
-   Do not infer an incident date from a repair date unless explicitly
    marked as a hypothesis.

## 4. Relationships and indexes

-   Claim has many Evidence, ExtractedFact, Evaluation,
    ReviewerDecision, and AuditEvent rows.
-   Evaluation has many Finding rows.
-   Evidence has many ExtractedFact rows.
-   Policy can be referenced by many claims but seeded policies are
    versioned and immutable after use.
-   Index `claim_number`, `status`, `submitted_at`, `claim_id`,
    `policy_id`, `sha256`, and `token_hash`.
