"""Idempotent demo seed. Evidence goes through the real upload/extraction pipeline."""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.claims import service
from app.db.models import Claim
from app.demo.fixtures import ensure_fixtures
from app.enums import EvidenceType as E, Uploader
from app.policies.catalog import seed_policies

MIME = {".png": "image/png", ".txt": "text/plain"}

DEMO = [
    dict(number="CP-DEMO-001", data=dict(
        product_type="LAPTOP", product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000123",
        claim_type="WARRANTY", policy_id="SYN-WAR-LAPTOP-01", event_type="HARDWARE_FAILURE", incident_date=date(2026, 6, 20),
        damage_or_failure_description="Laptop stopped powering on after a firmware update."),
        files=[("cp001_invoice.png", E.PURCHASE_INVOICE)]),
    dict(number="CP-DEMO-002", data=dict(
        product_type="LAPTOP", product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000456",
        claim_type="INSURANCE", policy_id="SYN-INS-LAPTOP-01", event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 10, 2),
        claimed_amount=Decimal("12500.00"), damage_or_failure_description="Screen cracked after slipping from a desk."),
        files=[("cp002_statement.txt", E.CUSTOMER_STATEMENT)]),
    dict(number="CP-DEMO-003", data=dict(
        product_type="LAPTOP", product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000789",
        claim_type="WARRANTY", policy_id="SYN-WAR-LAPTOP-01", event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 8, 10),
        damage_or_failure_description="Laptop was dropped and the chassis and screen were damaged."),
        files=[("cp003_invoice.png", E.PURCHASE_INVOICE)]),
    dict(number="CP-DEMO-004", data=dict(
        product_type="MOBILE_PHONE", product_brand="Aurora", product_model="A5", device_identifier="356938035643809",
        claim_type="INSURANCE", policy_id="SYN-INS-PHONE-01", event_type="ACCIDENTAL_DAMAGE", incident_date=date(2026, 10, 2),
        claimed_amount=Decimal("9800.00"), repair_already_performed=True,
        damage_or_failure_description="Phone display cracked after a fall."),
        files=[("cp004_invoice.png", E.PURCHASE_INVOICE), ("cp004_repair_receipt.png", E.REPAIR_RECEIPT)]),
]


def seed_demo(db: Session) -> list[str]:
    """Create demo claims that don't exist yet. Returns the numbers created."""
    seed_policies(db)
    fixtures = ensure_fixtures()
    created = []
    for spec in DEMO:
        if db.query(Claim).filter_by(claim_number=spec["number"]).first():
            continue
        claim = service.create_claim(db, spec["data"], claim_number=spec["number"])
        for fname, etype in spec["files"]:
            p = fixtures / fname
            service.ingest_evidence(db, claim, fname, MIME[p.suffix], p.read_bytes(), etype, Uploader.REVIEWER)
        service.evaluate_claim(db, claim)
        created.append(spec["number"])
    return created


if __name__ == "__main__":
    from app.db.session import SessionLocal, init_db
    init_db()
    with SessionLocal() as s:
        print("created:", seed_demo(s))
