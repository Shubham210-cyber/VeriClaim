# Synthetic Demo Policies and Claims

All names, devices, dates, amounts, and policies below are fictional.
Label the interface clearly as **Synthetic Hackathon Data --- Not a Real
Insurance Decision**.

## 1. Seeded policies

Keep policy rules in structured data, not only in prose.

### `SYN-WAR-LAPTOP-01`

-   Product: `LAPTOP`
-   Claim type: `WARRANTY`
-   Coverage window: 365 days from purchase for eligible
    hardware/manufacturing defects
-   Covered event codes: `MANUFACTURING_DEFECT`, `HARDWARE_FAILURE`
-   Excluded event codes: `ACCIDENTAL_DAMAGE`, `LIQUID_DAMAGE`, `THEFT`
-   Required evidence: purchase invoice, device identifier
-   Synthetic policy note: accidental physical damage is not covered by
    this warranty.

### `SYN-INS-LAPTOP-01`

-   Product: `LAPTOP`
-   Claim type: `INSURANCE`
-   Coverage window: 365 days from purchase for this demo plan
-   Covered event codes: `ACCIDENTAL_DAMAGE`, `LIQUID_DAMAGE`
-   Excluded event codes: `THEFT`, `COSMETIC_WEAR`
-   Required evidence: purchase invoice, device identifier, incident
    description; repair receipt if repair has already occurred
-   Max claim amount: INR 50,000
-   Deductible: INR 1,000

### `SYN-WAR-PHONE-01`

-   Product: `MOBILE_PHONE`
-   Claim type: `WARRANTY`
-   Coverage window: 365 days from purchase
-   Covered event codes: `MANUFACTURING_DEFECT`, `HARDWARE_FAILURE`
-   Excluded event codes: `ACCIDENTAL_DAMAGE`, `LIQUID_DAMAGE`, `THEFT`
-   Required evidence: purchase invoice, IMEI/device identifier

### `SYN-INS-PHONE-01`

-   Product: `MOBILE_PHONE`
-   Claim type: `INSURANCE`
-   Coverage window: 365 days from purchase
-   Covered event codes: `ACCIDENTAL_DAMAGE`, `LIQUID_DAMAGE`
-   Excluded event codes: `THEFT`, `COSMETIC_WEAR`
-   Required evidence: purchase invoice, IMEI/device identifier,
    incident description
-   Max claim amount: INR 30,000
-   Deductible: INR 750

## 2. Demo claims

### `CP-DEMO-001` --- Clean eligible laptop warranty claim

-   Product: Northstar N14 laptop
-   Purchase date: 2026-06-01
-   Incident date: 2026-06-20
-   Claim type: warranty
-   Event: hardware failure
-   Invoice model and identifier match claim
-   Required evidence present
-   Expected: `RECOMMENDED_APPROVAL`

### `CP-DEMO-002` --- Missing invoice

-   Product: Northstar N14 laptop
-   Claim type: insurance
-   Policy: `SYN-INS-LAPTOP-01`
-   No purchase invoice attached
-   Expected: `MORE_INFORMATION_REQUIRED`
-   Requested item: readable purchase invoice showing purchase date and
    device identity

### `CP-DEMO-003` --- Excluded accidental damage under warranty

-   Product: Northstar N14 laptop
-   Claim type: warranty
-   Policy: `SYN-WAR-LAPTOP-01`
-   Purchase invoice and identifier match
-   Reliable claim description says the laptop was dropped and the
    chassis/screen was damaged
-   Expected: `RECOMMENDED_REJECTION` because the synthetic warranty
    explicitly excludes accidental damage
-   Must not say fraud.

### `CP-DEMO-004` --- Contradictory dates

-   Product: mobile phone
-   Claim type: insurance
-   Claim says incident occurred 2026-10-02
-   Repair receipt is dated 2026-09-29 and appears to describe the same
    repair, but linkage is not conclusive
-   Expected: `HUMAN_REVIEW_REQUIRED` or `MORE_INFORMATION_REQUIRED`
-   Finding: repair date precedes reported incident date; request
    clarification
-   Must not automatically reject or call it fraud.

## 3. Important fixture design rules

-   Ensure each test fixture has expected findings and recommendation.
-   Do not rely on the LLM to create demo evidence or decide expected
    outcomes.
-   Use stable identifiers and dates so tests are reproducible.
-   Include at least one malformed or unreadable fixture for
    extraction-failure handling.
-   Clearly distinguish data entered by the customer from values
    extracted from documents.
-   Synthetic policy examples are demo rules, not legal advice or
    representations of real insurer coverage.
