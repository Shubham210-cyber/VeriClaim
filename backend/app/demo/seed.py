"""Idempotent example-claim seed. Evidence goes through the real upload/extraction pipeline.

Ten example claims cover every recommendation and a realistic mix of queue states (new, waiting for customer,
escalated, completed). Expected outcomes are asserted in tests/test_api.py.
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.claims import service
from app.db.models import Claim, utcnow
from app.demo.fixtures import ensure_fixtures
from app.enums import ClaimStatus, EvidenceType as E, Recommendation, ReviewerAction, Uploader
from app.policies.catalog import seed_policies

MIME = {".png": "image/png", ".txt": "text/plain", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

LAPTOP_WAR = dict(product_type="LAPTOP", claim_type="WARRANTY", policy_id="SYN-WAR-LAPTOP-01")
LAPTOP_INS = dict(product_type="LAPTOP", claim_type="INSURANCE", policy_id="SYN-INS-LAPTOP-01")
PHONE_WAR = dict(product_type="MOBILE_PHONE", claim_type="WARRANTY", policy_id="SYN-WAR-PHONE-01")
PHONE_INS = dict(product_type="MOBILE_PHONE", claim_type="INSURANCE", policy_id="SYN-INS-PHONE-01")

# `days_ago` staggers the submission time so the queue looks lived-in.
# `decision` (optional) is applied after the first review, to show claims in later states.
DEMO = [
    dict(number="CP-2026-1001", days_ago=1, expect=Recommendation.RECOMMENDED_APPROVAL, data=dict(
        LAPTOP_WAR, product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000123",
        event_type="HARDWARE_FAILURE", incident_date=date(2026, 6, 20),
        damage_or_failure_description="Laptop stopped powering on after a firmware update."),
        files=[("cp001_invoice.png", E.PURCHASE_INVOICE)]),
    dict(number="CP-2026-1002", days_ago=1, expect=Recommendation.MORE_INFORMATION_REQUIRED, data=dict(
        LAPTOP_INS, product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000456",
        event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 10, 2), claimed_amount=Decimal("12500.00"),
        damage_or_failure_description="Screen cracked after slipping from a desk."),
        files=[("cp002_statement.txt", E.CUSTOMER_STATEMENT)]),
    dict(number="CP-2026-1003", days_ago=2, expect=Recommendation.RECOMMENDED_REJECTION, data=dict(
        LAPTOP_WAR, product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000789",
        event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 8, 10),
        damage_or_failure_description="Laptop was dropped and the chassis and screen were damaged."),
        files=[("cp003_invoice.png", E.PURCHASE_INVOICE)]),
    dict(number="CP-2026-1004", days_ago=2, expect=Recommendation.HUMAN_REVIEW_REQUIRED, data=dict(
        PHONE_INS, product_brand="Aurora", product_model="A5", device_identifier="356938035643809",
        event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 10, 2), claimed_amount=Decimal("9800.00"),
        repair_already_performed=True, damage_or_failure_description="Phone display cracked after a fall."),
        files=[("cp004_invoice.png", E.PURCHASE_INVOICE), ("cp004_repair_receipt.png", E.REPAIR_RECEIPT)]),
    # Clean insurance claim with a payout estimate; already approved so the "Completed" group is populated.
    dict(number="CP-2026-1005", days_ago=6, expect=Recommendation.RECOMMENDED_APPROVAL, decision=(ReviewerAction.APPROVE, "Priya Nair"), data=dict(
        PHONE_INS, product_brand="Zenith", product_model="Z9 Pro", device_identifier="490154203237518",
        event_type="LIQUID_DAMAGE", incident_date=date(2026, 9, 2), claimed_amount=Decimal("11500.00"),
        damage_or_failure_description="Phone fell into water; screen and speaker stopped working."),
        files=[("cp005_invoice.png", E.PURCHASE_INVOICE)]),
    # IMEI on the invoice differs from the claim by two swapped digits: a clarification, not an accusation.
    dict(number="CP-2026-1006", days_ago=3, expect=Recommendation.HUMAN_REVIEW_REQUIRED, data=dict(
        PHONE_WAR, product_brand="Lumen", product_model="L3", device_identifier="352099001761481",
        event_type="HARDWARE_FAILURE", incident_date=date(2026, 8, 14),
        damage_or_failure_description="Phone restarts repeatedly and the battery drains in an hour."),
        files=[("cp006_invoice.png", E.PURCHASE_INVOICE)]),
    # Hardware failure is covered, but the incident is far outside the 12 month warranty.
    dict(number="CP-2026-1007", days_ago=4, expect=Recommendation.RECOMMENDED_REJECTION, data=dict(
        LAPTOP_WAR, product_brand="Northstar", product_model="N15", device_identifier="NS-N15-000842",
        event_type="HARDWARE_FAILURE", incident_date=date(2026, 9, 20),
        damage_or_failure_description="Keyboard stopped responding."),
        files=[("cp007_invoice.png", E.PURCHASE_INVOICE)]),
    # Claim exceeds the maximum payable amount: partial eligibility is a judgement call, so it is escalated.
    dict(number="CP-2026-1008", days_ago=5, expect=Recommendation.HUMAN_REVIEW_REQUIRED, decision=(ReviewerAction.ESCALATE, "Priya Nair"), data=dict(
        LAPTOP_INS, product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000555",
        event_type="LIQUID_DAMAGE", incident_date=date(2026, 9, 25), claimed_amount=Decimal("62000.00"),
        damage_or_failure_description="Coffee spilled on the keyboard; motherboard replacement quoted."),
        files=[("cp008_invoice.png", E.PURCHASE_INVOICE)]),
    # Purchase date printed as 06/04/2026: could be 6 April or 4 June, so the system refuses to guess.
    dict(number="CP-2026-1009", days_ago=0, expect=Recommendation.MORE_INFORMATION_REQUIRED, data=dict(
        PHONE_INS, product_brand="Vega", product_model="V1", device_identifier="861234050987654",
        event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 9, 28), claimed_amount=Decimal("7500.00"),
        damage_or_failure_description="Phone slipped from a pocket onto concrete."),
        files=[("cp009_invoice.png", E.PURCHASE_INVOICE)]),
    # Repair already carried out but no receipt yet; the reviewer has asked the customer, so it is "waiting".
    dict(number="CP-2026-1010", days_ago=3, expect=Recommendation.MORE_INFORMATION_REQUIRED, decision=(ReviewerAction.REQUEST_INFORMATION, "Priya Nair"), data=dict(
        PHONE_INS, product_brand="Nimbus", product_model="N2", device_identifier="867530123456780",
        event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 9, 15), claimed_amount=Decimal("6200.00"),
        repair_already_performed=True, damage_or_failure_description="Screen replaced at a local shop after a fall."),
        files=[("cp010_invoice.png", E.PURCHASE_INVOICE)]),
]


def _apply_decision(db: Session, claim: Claim, action: ReviewerAction, who: str) -> None:
    ev = service.latest_evaluation(db, claim.id)
    items = [{"item_type": m["item_type"], "description": m["description"]} for m in ev.missing_evidence] \
        if action == ReviewerAction.REQUEST_INFORMATION else []
    service.record_decision(db, claim, ev.id, action, None, items, who, expires_in_hours=72, max_uploads=5)


def seed_demo(db: Session) -> list[str]:
    """Create the example claims that don't exist yet. Returns the numbers created."""
    seed_policies(db)
    fixtures = ensure_fixtures()
    created = []
    for spec in DEMO:
        if db.query(Claim).filter_by(claim_number=spec["number"]).first():
            continue
        claim = service.create_claim(db, spec["data"], claim_number=spec["number"])
        claim.submitted_at = utcnow() - timedelta(days=spec["days_ago"], hours=(hash(spec["number"]) % 5) + 1)
        db.commit()
        for fname, etype in spec["files"]:
            p = fixtures / fname
            service.ingest_evidence(db, claim, fname, MIME[p.suffix], p.read_bytes(), etype, Uploader.REVIEWER)
        service.evaluate_claim(db, claim)
        if "decision" in spec:
            _apply_decision(db, claim, *spec["decision"])
        created.append(spec["number"])
    return created


if __name__ == "__main__":
    from app.db.session import SessionLocal, init_db
    init_db()
    with SessionLocal() as s:
        print("created:", seed_demo(s))
