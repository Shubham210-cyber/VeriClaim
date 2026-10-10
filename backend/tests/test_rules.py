"""Pure rule/aggregator tests: no DB, no AI."""
from datetime import date
from decimal import Decimal

from app.enums import FieldName as F, Recommendation as Rec, RuleResult as R
from app.rules.aggregator import aggregate
from app.rules.engine import ClaimView, Ctx, EvidenceView, FactView, PolicyView, run_rules


def policy(**kw):
    base = dict(id="P", product_type="LAPTOP", claim_type="WARRANTY", valid_from=None, valid_to=None, coverage_days=365,
                covered=["HARDWARE_FAILURE"], excluded=["ACCIDENTAL_DAMAGE"], max_amount=None, deductible=None,
                requires_purchase_proof=True, requires_identifier=True, required_types=["PURCHASE_INVOICE"],
                requires_incident_description=False, requires_repair_receipt_if_repaired=False, cap_is_ceiling=False)
    return PolicyView(**{**base, **kw})


def claim(**kw):
    base = dict(product_type="LAPTOP", claim_type="WARRANTY", event_type="HARDWARE_FAILURE", repair_performed=False,
                incident_date=date(2026, 6, 20), claimed_amount=None, currency="INR", description="x")
    return ClaimView(**{**base, **kw})


def cf(i, field, v, norm=None):
    return FactView(i, field.value, v, norm if norm is not None else v, 1.0, None, None, "CLAIM_RECORD")


def df(i, field, raw, norm="same", conf=0.95, ev="e1", et="PURCHASE_INVOICE"):
    return FactView(i, field.value, raw, raw if norm == "same" else norm, conf, ev, et, "DOCUMENT")


def good_facts():
    return [cf("c1", F.PRODUCT_MODEL, "Northstar N14", "northstar n14"), cf("c2", F.DEVICE_IDENTIFIER, "NS-1", "NS-1"),
            cf("c3", F.INCIDENT_DATE, "2026-06-20"),
            df("d1", F.PRODUCT_MODEL, "Northstar N14", "northstar n14"), df("d2", F.DEVICE_IDENTIFIER, "NS-1"),
            df("d3", F.PURCHASE_DATE, "2026-06-01")]


def ctx(facts=None, pol=None, cl=None, ev=True):
    evidence = [EvidenceView("e1", "PURCHASE_INVOICE", "SUCCEEDED", "h")] if ev else []
    return Ctx(cl or claim(), pol or policy(), evidence, good_facts() if facts is None else facts, 0.8)


def by_id(outs):
    return {o.rule_id.split("_")[0]: o for o in outs}


def rec(c):
    return aggregate(run_rules(c)).recommendation


def test_clean_claim_approved():
    assert rec(ctx()) == Rec.RECOMMENDED_APPROVAL


def test_is_deterministic():
    a = [(o.rule_id, o.result, o.explanation) for o in run_rules(ctx())]
    b = [(o.rule_id, o.result, o.explanation) for o in run_rules(ctx())]
    assert a == b


def test_missing_invoice_requests_information_not_rejection():
    facts = [f for f in good_facts() if f.source == "CLAIM_RECORD"]
    out = aggregate(run_rules(ctx(facts=facts, ev=False)))
    assert out.recommendation == Rec.MORE_INFORMATION_REQUIRED
    assert any(m["item_type"] == "PURCHASE_INVOICE" for m in out.missing_evidence)


def test_excluded_event_recommends_rejection_with_policy_reference():
    c = ctx(cl=claim(event_type="ACCIDENTAL_DAMAGE"))
    assert rec(c) == Rec.RECOMMENDED_REJECTION
    o = by_id(run_rules(c))["POL-006"]
    assert o.result == R.FAIL and "explicitly excluded" in o.explanation and "synthetic" not in o.explanation.lower() and o.reason_code == "EVENT_EXCLUDED"


def test_exclusion_outranks_missing_invoice():
    facts = [f for f in good_facts() if f.source == "CLAIM_RECORD"]
    assert rec(ctx(facts=facts, ev=False, cl=claim(event_type="ACCIDENTAL_DAMAGE"))) == Rec.RECOMMENDED_REJECTION


def test_conflict_outranks_exclusion():
    facts = good_facts()
    facts[-2] = df("d2", F.DEVICE_IDENTIFIER, "NS-999")
    assert rec(ctx(facts=facts, cl=claim(event_type="ACCIDENTAL_DAMAGE"))) == Rec.HUMAN_REVIEW_REQUIRED


def test_identifier_mismatch_cites_both_facts():
    facts = good_facts()
    facts[4] = df("d2", F.DEVICE_IDENTIFIER, "NS-999")
    o = by_id(run_rules(ctx(facts=facts)))["CON-002"]
    assert o.result == R.FAIL and {f.id for f in o.facts} == {"c2", "d2"}


def test_outside_window_is_rejection_candidate_when_dates_reliable():
    facts = good_facts()
    facts[-1] = df("d3", F.PURCHASE_DATE, "2024-01-01")
    assert rec(ctx(facts=facts)) == Rec.RECOMMENDED_REJECTION


def test_low_confidence_purchase_date_is_indeterminate_not_rejection():
    facts = good_facts()
    facts[-1] = df("d3", F.PURCHASE_DATE, "2024-01-01", conf=0.4)
    c = ctx(facts=facts)
    assert by_id(run_rules(c))["POL-003"].result == R.INDETERMINATE
    assert rec(c) == Rec.MORE_INFORMATION_REQUIRED


def test_ambiguous_date_is_indeterminate():
    facts = good_facts()
    facts[-1] = df("d3", F.PURCHASE_DATE, "03/04/2026", norm=None)
    assert by_id(run_rules(ctx(facts=facts)))["POL-003"].result == R.INDETERMINATE


def test_repair_before_incident_is_conflict_not_fraud():
    facts = good_facts() + [df("r1", F.REPAIR_DATE, "2026-06-10", ev="e2", et="REPAIR_RECEIPT")]
    c = ctx(facts=facts)
    o = by_id(run_rules(c))["CON-005"]
    assert o.result == R.FAIL and "fraud" in o.explanation.lower() and "not by itself" in o.explanation
    assert rec(c) == Rec.HUMAN_REVIEW_REQUIRED


def test_amount_mismatch_flagged_without_replacing_values():
    facts = good_facts() + [cf("c9", F.CLAIMED_AMOUNT, "9800.00"), df("r2", F.REPAIR_AMOUNT, "9000.00", ev="e2", et="REPAIR_RECEIPT")]
    o = by_id(run_rules(ctx(facts=facts)))["CON-006"]
    assert o.result == R.FAIL and "9800.00" in o.explanation and "9000.00" in o.explanation


def test_low_confidence_material_fact_flagged():
    facts = good_facts()
    facts[4] = df("d2", F.DEVICE_IDENTIFIER, "NS-1", conf=0.5)
    o = by_id(run_rules(ctx(facts=facts)))
    assert o["CON-008"].result == R.INDETERMINATE and o["CON-002"].result == R.INDETERMINATE


def test_unclassified_event_goes_to_human_review():
    assert rec(ctx(cl=claim(event_type="OTHER"))) == Rec.HUMAN_REVIEW_REQUIRED


def test_cap_exceeded_is_not_automatic_rejection():
    p = policy(claim_type="INSURANCE", covered=["ACCIDENTAL_DAMAGE"], excluded=[], max_amount=Decimal("1000"))
    c = ctx(pol=p, cl=claim(claim_type="INSURANCE", event_type="ACCIDENTAL_DAMAGE", claimed_amount=Decimal("5000")),
            facts=good_facts() + [cf("c9", F.CLAIMED_AMOUNT, "5000.00")])
    assert rec(c) == Rec.HUMAN_REVIEW_REQUIRED


def test_every_material_finding_has_source_or_explicit_note():
    for o in run_rules(ctx(cl=claim(event_type="ACCIDENTAL_DAMAGE"))):
        if o.result in (R.FAIL, R.INDETERMINATE):
            assert o.evidence_ids or o.facts or "No source fact" in o.explanation or "claim record" in o.explanation
