"""Pure deterministic rules. No DB, no AI: same inputs -> same outputs."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.enums import Category, EvidenceType, FactSource, FieldName, RuleResult, Severity

RULES_VERSION = "1.0.0"
R, S, C = RuleResult, Severity, Category
# Only fields that some rule actually relies on: a noisy value nobody uses must not block a claim.
MATERIAL = [FieldName.PRODUCT_MODEL, FieldName.DEVICE_IDENTIFIER, FieldName.PURCHASE_DATE,
            FieldName.INCIDENT_DATE, FieldName.REPAIR_DATE, FieldName.REPAIR_AMOUNT]


@dataclass
class FactView:
    id: str
    field_name: str
    raw: str
    norm: str | None
    conf: float | None
    evidence_id: str | None
    evidence_type: str | None
    source: str


@dataclass
class EvidenceView:
    id: str
    evidence_type: str
    status: str
    sha256: str
    dup_other_claim: bool = False


@dataclass
class ClaimView:
    product_type: str
    claim_type: str
    event_type: str | None
    repair_performed: bool
    incident_date: date | None
    claimed_amount: Decimal | None
    currency: str
    description: str | None


@dataclass
class PolicyView:
    id: str
    product_type: str
    claim_type: str
    valid_from: date | None
    valid_to: date | None
    coverage_days: int | None
    covered: list[str]
    excluded: list[str]
    max_amount: Decimal | None
    deductible: Decimal | None
    requires_purchase_proof: bool
    requires_identifier: bool
    required_types: list[str]
    requires_incident_description: bool
    requires_repair_receipt_if_repaired: bool
    cap_is_ceiling: bool


@dataclass
class RuleOutcome:
    rule_id: str
    result: RuleResult
    severity: Severity
    title: str
    explanation: str
    category: Category = Category.NONE
    facts: list[FactView] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    field_name: str | None = None
    recommended_action: str | None = None
    reason_code: str | None = None
    request: dict | None = None  # {"item_type":..., "description":...} for missing evidence


@dataclass
class Ctx:
    claim: ClaimView
    policy: PolicyView
    evidence: list[EvidenceView]  # latest version per evidence type
    facts: list[FactView]
    threshold: float

    def ev(self, etype: EvidenceType) -> EvidenceView | None:
        return next((e for e in self.evidence if e.evidence_type == etype.value), None)

    def claim_fact(self, f: FieldName) -> FactView | None:
        return next((x for x in self.facts if x.source == FactSource.CLAIM_RECORD.value and x.field_name == f.value), None)

    def doc_facts(self, f: FieldName, types: list[EvidenceType] | None = None) -> list[FactView]:
        tv = {t.value for t in types} if types else None
        return [x for x in self.facts if x.source == FactSource.DOCUMENT.value and x.field_name == f.value
                and (tv is None or x.evidence_type in tv)]

    def reliable(self, x: FactView | None) -> bool:
        return x is not None and x.norm is not None and (x.conf is None or x.conf >= self.threshold)

    def best_doc(self, f: FieldName, types: list[EvidenceType] | None = None) -> FactView | None:
        facts = self.doc_facts(f, types)
        return next((x for x in facts if self.reliable(x)), facts[0] if facts else None)


def _out(rule_id, result, severity, title, expl, category=C.NONE, facts=(), **kw) -> RuleOutcome:
    facts = [f for f in facts if f is not None]
    ev_ids = sorted({f.evidence_id for f in facts if f.evidence_id})
    if not facts:
        expl += " (No source fact is available for this finding.)"
    elif not ev_ids:
        expl += " (Source: claim record entered by the reviewer; no document page.)"
    return RuleOutcome(rule_id, result, severity, title, expl, category, list(facts), ev_ids, **kw)


def _na(rule_id, title) -> RuleOutcome:
    return RuleOutcome(rule_id, R.NOT_APPLICABLE, S.INFO, title, "Not applicable for this claim/policy.")


# ---------------------------------------------------------------- evidence
def ev_001(c: Ctx):
    t = "Purchase proof present"
    if not c.policy.requires_purchase_proof:
        return _na("EV-001_REQUIRED_PURCHASE_PROOF", t)
    if c.ev(EvidenceType.PURCHASE_INVOICE):
        return _out("EV-001_REQUIRED_PURCHASE_PROOF", R.PASS, S.INFO, t, "A purchase invoice has been uploaded.")
    return _out("EV-001_REQUIRED_PURCHASE_PROOF", R.FAIL, S.HIGH, "Purchase proof missing",
                "The selected policy requires proof of purchase and none has been uploaded.", C.MISSING,
                recommended_action="Request a readable purchase invoice showing model, device identifier and purchase date.",
                reason_code="MISSING_PURCHASE_PROOF",
                request={"item_type": "PURCHASE_INVOICE",
                         "description": "Upload a readable purchase invoice showing the device model, device identifier and purchase date."})


def ev_002(c: Ctx):
    t = "Device identifier available"
    if not c.policy.requires_identifier:
        return _na("EV-002_REQUIRED_DEVICE_IDENTIFIER", t)
    cf = c.claim_fact(FieldName.DEVICE_IDENTIFIER)
    df = c.best_doc(FieldName.DEVICE_IDENTIFIER)
    good = [x for x in (cf, df) if c.reliable(x)]
    if good:
        return _out("EV-002_REQUIRED_DEVICE_IDENTIFIER", R.PASS, S.INFO, t, "A reliable device identifier (serial/IMEI) is available.", facts=good)
    return _out("EV-002_REQUIRED_DEVICE_IDENTIFIER", R.FAIL, S.HIGH, "Device identifier missing or unreadable",
                "The policy requires a serial number/IMEI and none could be read reliably.", C.MISSING, facts=[df],
                recommended_action="Request a document that clearly shows the serial number/IMEI.",
                reason_code="MISSING_DEVICE_IDENTIFIER",
                request={"item_type": "PURCHASE_INVOICE", "description": "Upload a clear document showing the device serial number / IMEI."})


def ev_003(c: Ctx):
    t = "Repair receipt present"
    if not (c.policy.requires_repair_receipt_if_repaired and c.claim.repair_performed):
        return _na("EV-003_REQUIRED_REPAIR_RECEIPT", t)
    if c.ev(EvidenceType.REPAIR_RECEIPT):
        return _out("EV-003_REQUIRED_REPAIR_RECEIPT", R.PASS, S.INFO, t, "A repair receipt has been uploaded.")
    return _out("EV-003_REQUIRED_REPAIR_RECEIPT", R.FAIL, S.HIGH, "Repair receipt missing",
                "A repair was already performed and the policy requires the repair receipt.", C.MISSING,
                recommended_action="Request the repair/service receipt.", reason_code="MISSING_REPAIR_RECEIPT",
                request={"item_type": "REPAIR_RECEIPT", "description": "Upload the repair or service receipt."})


def ev_004(c: Ctx):
    needed = set(c.policy.required_types)
    if c.policy.requires_purchase_proof:
        needed.add(EvidenceType.PURCHASE_INVOICE.value)
    if c.policy.requires_repair_receipt_if_repaired and c.claim.repair_performed:
        needed.add(EvidenceType.REPAIR_RECEIPT.value)
    bad = [e for e in c.evidence if e.evidence_type in needed and e.status == "FAILED"]
    if not bad:
        return _out("EV-004_UNREADABLE_REQUIRED_EVIDENCE", R.PASS, S.INFO, "Required evidence readable", "All required documents could be read.")
    out = _out("EV-004_UNREADABLE_REQUIRED_EVIDENCE", R.INDETERMINATE, S.HIGH, "Required document unreadable",
               "Could not read: " + ", ".join(e.evidence_type for e in bad) + ". This is a technical limitation, not evidence the document lacks the data.",
               C.MISSING, recommended_action="Request a clearer copy.", reason_code="UNREADABLE_REQUIRED_EVIDENCE",
               request={"item_type": bad[0].evidence_type, "description": "Upload a clearer, higher-resolution copy of this document."})
    out.evidence_ids = [e.id for e in bad]
    return out


def ev_005(c: Ctx):
    t = "Incident details provided"
    if not c.policy.requires_incident_description:
        return _na("EV-005_REQUIRED_INCIDENT_INFO", t)
    has_date = c.claim.incident_date is not None
    has_desc = bool((c.claim.description or "").strip()) or bool(c.doc_facts(FieldName.EVENT_DESCRIPTION, [EvidenceType.CUSTOMER_STATEMENT]))
    if has_date and has_desc:
        return _out("EV-005_REQUIRED_INCIDENT_INFO", R.PASS, S.INFO, t, "Incident date and description are present.",
                    facts=[c.claim_fact(FieldName.INCIDENT_DATE)])
    return _out("EV-005_REQUIRED_INCIDENT_INFO", R.FAIL, S.HIGH, "Incident details missing",
                "The policy requires an incident date and description.", C.MISSING, reason_code="MISSING_INCIDENT_INFO",
                recommended_action="Request a statement with the incident date and description.",
                request={"item_type": "CUSTOMER_STATEMENT", "description": "Provide a statement with the incident date and what happened."})


# ---------------------------------------------------------------- policy
def pol_001(c: Ctx):
    t = "Product type matches policy"
    if c.claim.product_type == c.policy.product_type:
        return _out("POL-001_PRODUCT_TYPE_MATCH", R.PASS, S.INFO, t, "Claim product matches the policy product.")
    return _out("POL-001_PRODUCT_TYPE_MATCH", R.FAIL, S.HIGH, "Product type does not match policy",
                f"Claim is for {c.claim.product_type}; policy covers {c.policy.product_type}.", C.REJECTION_CANDIDATE,
                reason_code="PRODUCT_TYPE_MISMATCH", recommended_action="Confirm the correct policy was selected.")


def pol_002(c: Ctx):
    t = "Claim type matches policy"
    if c.claim.claim_type == c.policy.claim_type:
        return _out("POL-002_CLAIM_TYPE_MATCH", R.PASS, S.INFO, t, "Claim type matches the policy.")
    return _out("POL-002_CLAIM_TYPE_MATCH", R.FAIL, S.HIGH, "Claim type does not match policy",
                f"Claim is {c.claim.claim_type}; policy is {c.policy.claim_type}.", C.REJECTION_CANDIDATE,
                reason_code="CLAIM_TYPE_MISMATCH", recommended_action="Confirm the correct policy was selected.")


def pol_003(c: Ctx):
    rid, t = "POL-003_PURCHASE_COVERAGE_WINDOW", "Within coverage window"
    if c.policy.coverage_days is None:
        return _na(rid, t)
    inc = c.claim_fact(FieldName.INCIDENT_DATE)
    pur = c.best_doc(FieldName.PURCHASE_DATE, [EvidenceType.PURCHASE_INVOICE])
    if c.claim.incident_date is None:
        return _out(rid, R.INDETERMINATE, S.MEDIUM, "Coverage window cannot be checked", "Incident date is missing.", C.MISSING,
                    reason_code="INCIDENT_DATE_UNKNOWN", recommended_action="Provide the incident date.")
    if pur is None:
        return _out(rid, R.INDETERMINATE, S.MEDIUM, "Coverage window cannot be checked",
                    "No purchase date is available (purchase invoice missing).", C.MISSING, facts=[inc],
                    reason_code="PURCHASE_DATE_UNKNOWN", recommended_action="Obtain the purchase invoice.")
    if not c.reliable(pur):
        return _out(rid, R.INDETERMINATE, S.MEDIUM, "Coverage window cannot be checked",
                    "The purchase date could not be read reliably (low OCR confidence or ambiguous date format).", C.CLARIFY,
                    facts=[inc, pur], reason_code="PURCHASE_DATE_UNRELIABLE", recommended_action="Request a clearer invoice or confirm the date.",
                    request={"item_type": "PURCHASE_INVOICE", "description": "Upload a clearer invoice with an unambiguous purchase date."})
    days = (c.claim.incident_date - date.fromisoformat(pur.norm)).days
    if days < 0:
        return _out(rid, R.FAIL, S.HIGH, "Incident precedes purchase",
                    f"Reported incident date is {-days} day(s) before the purchase date on the invoice. Needs clarification.",
                    C.CONFLICT, facts=[inc, pur], reason_code="INCIDENT_BEFORE_PURCHASE", recommended_action="Clarify dates with the customer.")
    if days > c.policy.coverage_days:
        return _out(rid, R.FAIL, S.HIGH, "Outside coverage window",
                    f"Incident was {days} days after purchase; the synthetic policy covers {c.policy.coverage_days} days.",
                    C.REJECTION_CANDIDATE, facts=[inc, pur], reason_code="OUTSIDE_COVERAGE_WINDOW")
    return _out(rid, R.PASS, S.INFO, t, f"Incident was {days} days after purchase (limit {c.policy.coverage_days}).", facts=[inc, pur])


def pol_004(c: Ctx):
    rid, t = "POL-004_POLICY_EFFECTIVE_DATES", "Within policy effective dates"
    if not (c.policy.valid_from or c.policy.valid_to):
        return _na(rid, t)
    if c.claim.incident_date is None:
        return _out(rid, R.INDETERMINATE, S.MEDIUM, t, "Incident date is missing.", C.MISSING, reason_code="INCIDENT_DATE_UNKNOWN")
    d, inc = c.claim.incident_date, c.claim_fact(FieldName.INCIDENT_DATE)
    if (c.policy.valid_from and d < c.policy.valid_from) or (c.policy.valid_to and d > c.policy.valid_to):
        return _out(rid, R.FAIL, S.HIGH, "Outside policy effective dates", "Incident date is outside the policy's effective period.",
                    C.REJECTION_CANDIDATE, facts=[inc], reason_code="OUTSIDE_POLICY_DATES")
    return _out(rid, R.PASS, S.INFO, t, "Incident date is within the policy period.", facts=[inc])


def pol_005(c: Ctx):
    rid, t = "POL-005_EVENT_COVERED", "Event type covered"
    et = c.claim.event_type
    if et in c.policy.excluded:
        return _na(rid, t)  # handled by POL-006
    if et is None or et == "OTHER":
        return _out(rid, R.INDETERMINATE, S.MEDIUM, "Event type not classified",
                    "The event type is unclassified; a reviewer must classify it before coverage can be decided.", C.AMBIGUOUS,
                    reason_code="EVENT_UNCLASSIFIED", recommended_action="Select the event type.")
    if et in c.policy.covered:
        return _out(rid, R.PASS, S.INFO, t, f"{et} is a covered event under this synthetic policy.", facts=[c.claim_fact(FieldName.EVENT_DESCRIPTION)])
    return _out(rid, R.FAIL, S.MEDIUM, "Event not listed as covered",
                f"{et} is neither covered nor explicitly excluded by this policy; reviewer judgment needed.", C.AMBIGUOUS,
                facts=[c.claim_fact(FieldName.EVENT_DESCRIPTION)], reason_code="EVENT_NOT_COVERED")


def pol_006(c: Ctx):
    rid, t = "POL-006_EVENT_EXCLUDED", "Event not excluded"
    et = c.claim.event_type
    if et and et in c.policy.excluded:
        return _out(rid, R.FAIL, S.HIGH, "Event explicitly excluded by policy",
                    f"The reviewer-classified event {et} is explicitly excluded by synthetic policy {c.policy.id}.",
                    C.REJECTION_CANDIDATE, facts=[c.claim_fact(FieldName.EVENT_DESCRIPTION)],
                    reason_code="EVENT_EXCLUDED", recommended_action="Confirm classification, then reject citing the policy exclusion.")
    if et and et != "OTHER":
        return _out(rid, R.PASS, S.INFO, t, f"{et} is not excluded by this policy.")
    return _na(rid, t)


def pol_007(c: Ctx):
    rid, t = "POL-007_CLAIM_AMOUNT_LIMIT", "Claim amount within limit"
    if c.policy.max_amount is None or c.claim.claimed_amount is None:
        return _na(rid, t)
    cf = c.claim_fact(FieldName.CLAIMED_AMOUNT)
    if c.claim.claimed_amount <= c.policy.max_amount:
        return _out(rid, R.PASS, S.INFO, t, f"Claimed {c.claim.claimed_amount} is within the maximum {c.policy.max_amount}.", facts=[cf])
    if c.policy.cap_is_ceiling:
        return _out(rid, R.FAIL, S.HIGH, "Claim exceeds eligibility ceiling", f"Claimed {c.claim.claimed_amount} exceeds the ceiling {c.policy.max_amount}.",
                    C.REJECTION_CANDIDATE, facts=[cf], reason_code="AMOUNT_OVER_CEILING")
    return _out(rid, R.FAIL, S.MEDIUM, "Claim exceeds maximum payable amount",
                f"Claimed {c.claim.claimed_amount} exceeds the maximum {c.policy.max_amount}; partial eligibility, reviewer judgment needed.",
                C.AMBIGUOUS, facts=[cf], reason_code="AMOUNT_OVER_CAP")


def pol_008(c: Ctx):
    rid, t = "POL-008_DEDUCTIBLE_CALCULATION", "Illustrative eligible amount (estimate)"
    if c.claim.claimed_amount is None or c.policy.deductible is None:
        return _na(rid, t)
    base = min(c.claim.claimed_amount, c.policy.max_amount) if c.policy.max_amount else c.claim.claimed_amount
    est = max(Decimal("0"), base - c.policy.deductible)
    return _out(rid, R.PASS, S.INFO, t,
                f"ESTIMATE ONLY, not a settlement promise: min(claimed, cap) {base} - deductible {c.policy.deductible} = {est} {c.claim.currency}.",
                C.NOTE, facts=[c.claim_fact(FieldName.CLAIMED_AMOUNT)])


# ---------------------------------------------------------------- consistency
def con_001(c: Ctx):
    rid, t = "CON-001_PRODUCT_MODEL_MISMATCH", "Invoice model matches claim"
    cf, df = c.claim_fact(FieldName.PRODUCT_MODEL), c.best_doc(FieldName.PRODUCT_MODEL, [EvidenceType.PURCHASE_INVOICE])
    if cf is None or df is None:
        return _na(rid, t)
    if not (c.reliable(cf) and c.reliable(df)):
        return _out(rid, R.INDETERMINATE, S.MEDIUM, "Product model could not be confirmed",
                    f"The claim says '{cf.raw}'; the closest text on the document is '{df.raw}', which could not be read "
                    "reliably enough to compare. A clearer copy or a manual check is needed.", C.CLARIFY, facts=[cf, df],
                    reason_code="LOW_CONFIDENCE_MODEL", recommended_action="Verify the model against the original document.",
                    request={"item_type": "PURCHASE_INVOICE", "description": "Upload a clearer invoice that shows the product model."})
    a, b = cf.norm, df.norm
    if a == b or a in b or b in a:
        return _out(rid, R.PASS, S.INFO, t, f"Claim model '{cf.raw}' matches invoice model '{df.raw}'.", facts=[cf, df])
    return _out(rid, R.FAIL, S.HIGH, "Product model differs between claim and invoice",
                f"Claim says '{cf.raw}'; invoice says '{df.raw}'. This is an inconsistency needing clarification, not proof of wrongdoing.",
                C.CONFLICT, facts=[cf, df], reason_code="MODEL_MISMATCH", recommended_action="Ask the customer to clarify.")


def con_002(c: Ctx):
    rid, t = "CON-002_IDENTIFIER_MISMATCH", "Serial/IMEI matches"
    cf, df = c.claim_fact(FieldName.DEVICE_IDENTIFIER), c.best_doc(FieldName.DEVICE_IDENTIFIER)
    if cf is None or df is None:
        return _na(rid, t)
    if not (c.reliable(cf) and c.reliable(df)):
        return _out(rid, R.INDETERMINATE, S.MEDIUM, t, "Identifier could not be read reliably; not compared.", C.CLARIFY,
                    facts=[cf, df], reason_code="LOW_CONFIDENCE_IDENTIFIER",
                    request={"item_type": "PURCHASE_INVOICE", "description": "Upload a clearer document showing the serial number / IMEI."})
    if cf.norm == df.norm:
        return _out(rid, R.PASS, S.INFO, t, f"Identifier '{cf.raw}' matches the document.", facts=[cf, df])
    return _out(rid, R.FAIL, S.HIGH, "Device identifier differs",
                f"Claim identifier '{cf.raw}' differs from document identifier '{df.raw}'. Needs clarification; this may be a typo or OCR issue.",
                C.CONFLICT, facts=[cf, df], reason_code="IDENTIFIER_MISMATCH", recommended_action="Verify the identifier with the customer.")


def con_003(c: Ctx):
    rid, t = "CON-003_PURCHASE_DATE_MISMATCH", "Purchase dates consistent"
    facts = [f for f in c.doc_facts(FieldName.PURCHASE_DATE) if c.reliable(f)]
    if len({f.evidence_id for f in facts}) < 2:
        return _na(rid, t)
    if len({f.norm for f in facts}) == 1:
        return _out(rid, R.PASS, S.INFO, t, "All documents give the same purchase date.", facts=facts)
    return _out(rid, R.FAIL, S.HIGH, "Purchase dates differ across documents",
                "Documents disagree on the purchase date: " + "; ".join(f"{f.raw} ({f.evidence_type})" for f in facts),
                C.CONFLICT, facts=facts, reason_code="PURCHASE_DATE_MISMATCH")


def con_004(c: Ctx):
    rid, t = "CON-004_INCIDENT_DATE_CONFLICT", "Incident dates consistent"
    cf = c.claim_fact(FieldName.INCIDENT_DATE)
    docs = [f for f in c.doc_facts(FieldName.INCIDENT_DATE) if c.reliable(f)]
    if cf is None or not docs:
        return _na(rid, t)
    bad = [f for f in docs if f.norm != cf.norm]
    if not bad:
        return _out(rid, R.PASS, S.INFO, t, "Incident date matches supporting documents.", facts=[cf, *docs])
    return _out(rid, R.FAIL, S.HIGH, "Incident date differs from supporting document",
                f"Claim date {cf.raw}; document states {bad[0].raw}. Needs clarification.", C.CONFLICT, facts=[cf, *bad],
                reason_code="INCIDENT_DATE_CONFLICT")


def con_005(c: Ctx):
    rid, t = "CON-005_REPAIR_PRECEDES_INCIDENT", "Repair follows incident"
    cf, rf = c.claim_fact(FieldName.INCIDENT_DATE), c.best_doc(FieldName.REPAIR_DATE, [EvidenceType.REPAIR_RECEIPT])
    if rf is None or cf is None:
        return _na(rid, t)
    if not (c.reliable(cf) and c.reliable(rf)):
        return _out(rid, R.INDETERMINATE, S.MEDIUM, t, "Repair date could not be read reliably.", C.CLARIFY, facts=[cf, rf], reason_code="LOW_CONFIDENCE_REPAIR_DATE")
    if date.fromisoformat(rf.norm) < date.fromisoformat(cf.norm):
        return _out(rid, R.FAIL, S.HIGH, "Repair receipt predates reported incident",
                    f"The repair receipt is dated {rf.raw}, before the reported incident date {cf.raw}. The receipt may relate to an earlier "
                    "event or a date may be wrong; this needs clarification and is not by itself an indication of fraud.",
                    C.CONFLICT, facts=[cf, rf], reason_code="REPAIR_PRECEDES_INCIDENT", recommended_action="Ask the customer to clarify the timeline.")
    return _out(rid, R.PASS, S.INFO, t, "Repair date is on or after the incident date.", facts=[cf, rf])


def con_006(c: Ctx):
    rid, t = "CON-006_AMOUNT_MISMATCH", "Claimed amount matches repair invoice"
    cf, rf = c.claim_fact(FieldName.CLAIMED_AMOUNT), c.best_doc(FieldName.REPAIR_AMOUNT, [EvidenceType.REPAIR_RECEIPT])
    if cf is None or rf is None:
        return _na(rid, t)
    if not (c.reliable(cf) and c.reliable(rf)):
        return _out(rid, R.INDETERMINATE, S.MEDIUM, t, "Repair amount could not be read reliably.", C.CLARIFY, facts=[cf, rf], reason_code="LOW_CONFIDENCE_AMOUNT")
    if Decimal(cf.norm) == Decimal(rf.norm):
        return _out(rid, R.PASS, S.INFO, t, "Claimed amount equals the repair receipt amount.", facts=[cf, rf])
    return _out(rid, R.FAIL, S.MEDIUM, "Claimed amount differs from repair receipt",
                f"Claimed {cf.norm}; repair receipt shows {rf.norm}. Neither value was altered; clarification needed.", C.CLARIFY,
                facts=[cf, rf], reason_code="AMOUNT_MISMATCH", recommended_action="Ask the customer to explain the difference.")


def con_007(c: Ctx):
    rid, t = "CON-007_DUPLICATE_FILE_HASH", "No duplicate files"
    dups = [e for e in c.evidence if e.dup_other_claim]
    by_hash: dict[str, set[str]] = {}
    for e in c.evidence:
        by_hash.setdefault(e.sha256, set()).add(e.evidence_type)
    in_claim = [h for h, types in by_hash.items() if len(types) > 1]
    if not dups and not in_claim:
        return _out(rid, R.PASS, S.INFO, t, "No identical files found on other claims or reused across document types.")
    out = _out(rid, R.FAIL, S.LOW, "Identical file reused", "An identical file appears on another claim or under multiple document types. "
               "Flagged for reviewer awareness only; this does not affect the recommendation.", C.NOTE, reason_code="DUPLICATE_FILE_HASH")
    out.evidence_ids = [e.id for e in dups]
    return out


def con_008(c: Ctx):
    rid, t = "CON-008_LOW_CONFIDENCE_EXTRACTION", "Extraction confidence adequate"
    low = [f for f in c.facts if f.source == FactSource.DOCUMENT.value and f.field_name in {m.value for m in MATERIAL}
           and (f.norm is None or (f.conf is not None and f.conf < c.threshold))]
    if not low:
        return _out(rid, R.PASS, S.INFO, t, "All material extracted facts meet the confidence threshold.")
    return _out(rid, R.INDETERMINATE, S.MEDIUM, "Low-confidence or unparseable extraction",
                "These values could not be verified reliably: " + ", ".join(sorted({f.field_name for f in low})) +
                ". Confidence is a routing heuristic, not truth.", C.CLARIFY, facts=low, reason_code="LOW_CONFIDENCE_EXTRACTION",
                recommended_action="Request clearer documents or verify manually.")


def con_009(c: Ctx):
    rid, t = "CON-009_CURRENCY_MISMATCH", "Currency consistent"
    docs = [f for f in c.doc_facts(FieldName.CURRENCY) if f.norm]
    if not docs or c.claim.claimed_amount is None:
        return _na(rid, t)
    bad = [f for f in docs if f.norm != c.claim.currency]
    if not bad:
        return _out(rid, R.PASS, S.INFO, t, "Document currency matches the claim.", facts=docs)
    return _out(rid, R.FAIL, S.MEDIUM, "Currency differs", f"Claim currency {c.claim.currency}; document shows {bad[0].norm}.", C.CLARIFY,
                facts=bad, reason_code="CURRENCY_MISMATCH")


ALL_RULES = [ev_001, ev_002, ev_003, ev_004, ev_005, pol_001, pol_002, pol_003, pol_004, pol_005, pol_006,
             pol_007, pol_008, con_001, con_002, con_003, con_004, con_005, con_006, con_007, con_008, con_009]


def run_rules(ctx: Ctx) -> list[RuleOutcome]:
    return [r(ctx) for r in ALL_RULES]
