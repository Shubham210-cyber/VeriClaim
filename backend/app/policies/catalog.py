"""Bundled cover definitions. Rules live in structured data."""
from sqlalchemy.orm import Session

from app.db.models import Policy

_HW = ["MANUFACTURING_DEFECT", "HARDWARE_FAILURE"]
_ACC = ["ACCIDENTAL_DAMAGE", "LIQUID_DAMAGE"]

POLICIES = [
    dict(
        id="SYN-WAR-LAPTOP-01", name="Laptop Manufacturer Warranty (12 months)", product_type="LAPTOP",
        claim_type="WARRANTY", coverage_days_from_purchase=365,
        covered_event_types=_HW, excluded_event_types=["ACCIDENTAL_DAMAGE", "LIQUID_DAMAGE", "THEFT"],
        required_evidence_types=["PURCHASE_INVOICE"], requires_incident_description=False,
        note="Accidental physical damage is not covered by this warranty.",
    ),
    dict(
        id="SYN-INS-LAPTOP-01", name="Laptop Accidental Damage Cover (12 months)", product_type="LAPTOP",
        claim_type="INSURANCE", coverage_days_from_purchase=365,
        covered_event_types=_ACC, excluded_event_types=["THEFT", "COSMETIC_WEAR"],
        required_evidence_types=["PURCHASE_INVOICE"], requires_incident_description=True,
        requires_repair_receipt_if_repaired=True,
        max_claim_amount="50000.00", deductible_amount="1000.00",
        note="Repair receipt required if a repair has already occurred.",
    ),
    dict(
        id="SYN-WAR-PHONE-01", name="Phone Manufacturer Warranty (12 months)", product_type="MOBILE_PHONE",
        claim_type="WARRANTY", coverage_days_from_purchase=365,
        covered_event_types=_HW, excluded_event_types=["ACCIDENTAL_DAMAGE", "LIQUID_DAMAGE", "THEFT"],
        required_evidence_types=["PURCHASE_INVOICE"], note="The IMEI is used as the device identifier.",
    ),
    dict(
        id="SYN-INS-PHONE-01", name="Phone Accidental Damage Cover (12 months)", product_type="MOBILE_PHONE",
        claim_type="INSURANCE", coverage_days_from_purchase=365,
        covered_event_types=_ACC, excluded_event_types=["THEFT", "COSMETIC_WEAR"],
        required_evidence_types=["PURCHASE_INVOICE"], requires_incident_description=True,
        requires_repair_receipt_if_repaired=True,
        max_claim_amount="30000.00", deductible_amount="750.00",
        note="The IMEI is used as the device identifier.",
    ),
]


def seed_policies(db: Session) -> None:
    for p in POLICIES:
        row = db.get(Policy, (p["id"], "1"))
        if row is None:
            db.add(Policy(policy_version="1", **p))
        else:  # display text only; coverage terms of a used policy version are never changed
            row.name, row.note = p["name"], p.get("note", "")
    db.commit()


def policy_names(db: Session) -> dict[tuple[str, str], str]:
    return {(p.id, p.policy_version): p.name for p in db.query(Policy).all()}
