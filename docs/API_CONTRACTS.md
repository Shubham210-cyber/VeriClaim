# API Contracts

Prefix all endpoints with `/api/v1`. Use JSON except file-upload
endpoints. Return consistent errors:

``` json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The uploaded file is not supported.",
    "request_id": "optional-request-id"
  }
}
```

## 1. Health and policies

### `GET /health`

Returns `{ "status": "ok", "ai_provider": "mock" }`. Never return
secrets.

### `GET /api/v1/policies`

Returns seeded synthetic policies, their product/claim types, versions,
and display labels.

### `GET /api/v1/policies/{policy_id}`

Returns the explicit structured rules for one policy. Mark every policy
as synthetic demo data.

## 2. Claims

### `GET /api/v1/claims`

Query params: `status`, `product_type`, `claim_type`, `q`, `limit`
(default 25, max 100), `offset`. Returns paginated claim summaries.

### `POST /api/v1/claims`

Request:

``` json
{
  "product_type": "LAPTOP",
  "product_brand": "Northstar",
  "product_model": "N14",
  "device_identifier": "NS-N14-000123",
  "claim_type": "INSURANCE",
  "policy_id": "SYN-INS-LAPTOP-01",
  "incident_date": "2026-10-02",
  "claimed_amount": "12500.00",
  "currency": "INR",
  "damage_or_failure_description": "Screen damaged after accidental drop"
}
```

Response: `201` with claim ID, claim number, status, and timestamps.

### `GET /api/v1/claims/{claim_id}`

Returns claim overview, latest evaluation summary, evidence metadata,
findings, reviewer decisions, and timeline. Never expose storage paths
or upload token hashes.

### `POST /api/v1/claims/{claim_id}/evaluate`

Starts/re-runs extraction/rules/evaluation synchronously for the MVP.
Response includes `evaluation_id`, recommendation, rule results,
findings, missing evidence, and provider mode. If later made
asynchronous, return `202` and a job ID, but do not implement a queue in
the 3-hour MVP.

### `GET /api/v1/claims/{claim_id}/evaluations`

Returns evaluations newest first, preserving prior results.

## 3. Evidence uploads

### `POST /api/v1/claims/{claim_id}/evidence`

Multipart fields: - `file`: one allowed file - `evidence_type`:
EvidenceType

Allowed MVP file types: PDF, PNG, JPEG, TXT. Suggested max size: 10
MB/file. Return evidence metadata and extraction status. Do not return
the internal storage key.

### `GET /api/v1/claims/{claim_id}/evidence/{evidence_id}`

Returns safe metadata, extraction status, and facts. Original file
retrieval should be a separate authenticated/authorized endpoint; for a
demo without reviewer authentication, restrict access to the local
reviewer UI and never expose arbitrary file paths.

### `GET /api/v1/claims/{claim_id}/evidence/{evidence_id}/download`

Streams only the file that belongs to that claim after checking access.
Set safe content disposition and MIME.

## 4. Reviewer decisions

### `POST /api/v1/claims/{claim_id}/decisions`

Request:

``` json
{
  "evaluation_id": "evaluation-uuid",
  "action": "REQUEST_INFORMATION",
  "reason": "Purchase proof is required by the selected policy.",
  "requested_items": [
    {
      "item_type": "PURCHASE_INVOICE",
      "description": "Upload a readable purchase invoice showing the device model and purchase date."
    }
  ]
}
```

Response includes the persisted decision, updated claim status, and
optional upload link (return the raw link token only at creation time).

Validation: - `evaluation_id` must belong to the claim. - Rejection and
recommendation overrides require a non-empty reason. -
`REQUEST_INFORMATION` requires at least one requested item. - Every
action creates an audit event.

## 5. Customer upload link

### `POST /api/v1/claims/{claim_id}/upload-requests`

Reviewer-side endpoint. Request includes structured requested items,
expiry duration (bounded, e.g. 1--72 hours), and max uploads (bounded).
Return a raw high-entropy token once and a URL such as
`/customer-upload/{token}`. Store only a cryptographic hash of the
token.

### `GET /api/v1/public/upload-requests/{token}`

Public token-scoped endpoint. Returns only the claim reference/display
label, requested items, expiry, and remaining upload count. It must not
expose internal findings, policy notes, reviewer identity, other
evidence, or claim details beyond what is needed for upload.

### `POST /api/v1/public/upload-requests/{token}/evidence`

Multipart file and evidence type. Validate token hash, expiry,
revocation, allowed types, remaining count, file limits, and claim
scope. Append evidence as a new version and audit the upload. After
upload, mark the claim for re-evaluation or `AWAITING_REVIEW`.

Do not allow public endpoints to list claims, access reviewer endpoints,
or create arbitrary upload requests.

## 6. Audit

### `GET /api/v1/claims/{claim_id}/audit`

Returns chronological audit events with secrets and raw document
contents excluded.

## 7. HTTP status guidance

-   `200`: successful read/action
-   `201`: created
-   `202`: accepted for future asynchronous implementation only
-   `400`: invalid state transition/request
-   `401/403`: unauthorized or token scope denied (if auth is
    implemented)
-   `404`: claim/evidence/token not found
-   `413`: upload too large
-   `415`: unsupported file type
-   `422`: schema validation error
-   `500`: unexpected error with generic client message and server-side
    logs

## 8. Contract rules

-   Use UUIDs for internal IDs; use human-readable claim numbers only
    for display.
-   Use ISO dates and UTC ISO datetimes.
-   Serialize money as decimal strings.
-   Use pagination for claim lists.
-   Pydantic models define request/response schemas.
-   Keep route handlers thin; call service functions.
-   Add OpenAPI examples for the core workflow.
