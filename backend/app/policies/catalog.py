"""Seeded SYNTHETIC policies (docs/DEMO_DATA.md). Rules live in structured data."""
from sqlalchemy.orm import Session

from app.db.models import Policy

_HW = ["MANUFACTURING_DEFECT", "HARDWARE_FAILURE"]
_ACC = ["ACCIDENTAL_DAMAGE", "LIQUID_DAMAGE"]

POLICIES = [
    dict(
        id="SYN-WAR-LAPTOP-01", name="Synthetic Laptop Warranty (365d)", product_type="LAPTOP",
        claim_type="WARRANTY", coverage_days_from_purchase=365,
        covered_event_types=_HW, excluded_event_types=["ACCIDENTAL_DAMAGE", "LIQUID_DAMAGE", "THEFT"],
        required_evidence_types=["PURCHASE_INVOICE"], requires_incident_description=False,
        note="Accidental physical damage is not covered by this warranty.",
    ),
    dict(
        id="SYN-INS-LAPTOP-01", name="Synthetic Laptop Insurance (365d)", product_type="LAPTOP",
        claim_type="INSURANCE", coverage_days_from_purchase=365,
        covered_event_types=_ACC, excluded_event_types=["THEFT", "COSMETIC_WEAR"],
        required_evidence_types=["PURCHASE_INVOICE"], requires_incident_description=True,
        requires_repair_receipt_if_repaired=True,
        max_claim_amount="50000.00", deductible_amount="1000.00",
        note="Repair receipt required if a repair has already occurred.",
    ),
    dict(
        id="SYN-WAR-PHONE-01", name="Synthetic Phone Warranty (365d)", product_type="MOBILE_PHONE",
        claim_type="WARRANTY", coverage_days_from_purchase=365,
        covered_event_types=_HW, excluded_event_types=["ACCIDENTAL_DAMAGE", "LIQUID_DAMAGE", "THEFT"],
        required_evidence_types=["PURCHASE_INVOICE"], note="IMEI is the device identifier.",
    ),
    dict(
        id="SYN-INS-PHONE-01", name="Synthetic Phone Insurance (365d)", product_type="MOBILE_PHONE",
        claim_type="INSURANCE", coverage_days_from_purchase=365,
        covered_event_types=_ACC, excluded_event_types=["THEFT", "COSMETIC_WEAR"],
        required_evidence_types=["PURCHASE_INVOICE"], requires_incident_description=True,
        requires_repair_receipt_if_repaired=True,
        max_claim_amount="30000.00", deductible_amount="750.00",
        note="IMEI is the device identifier.",
    ),
]


def seed_policies(db: Session) -> None:
    for p in POLICIES:
        if db.get(Policy, (p["id"], "1")) is None:
            db.add(Policy(policy_version="1", **p))
    db.commit()
