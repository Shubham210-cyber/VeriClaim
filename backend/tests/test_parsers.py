"""Parsers on messy marketplace-style invoice text, plus OCR on a generated complex invoice."""
from pathlib import Path
from decimal import Decimal

import pytest

from app.config import settings
from app.documents.extract import ExtractionResult, PageText
from app.enums import EvidenceType as E, ExtractionMethod, FieldName as F
from app.normalization.parsers import Hints, parse_amount, parse_date, parse_document, words_to_number
from tests.conftest import make_claim, upload

MESSY = """Sold By: Fake Mart Limited
GST Registration No: 19AAACL5662Q01ZT
Order Number: 171-9054163-6711503 Invoice Number: QEAC-7547
Order Date: 30.03.2018 Invoice Details: WB-QEAC-143189331-1718
Invoice Date: 30.03.2018
SI. Description Unit Price Qty Net Amount Tax
1 Nokia 2 (Pewter/Black) | B07846F3SX ( Nokia 2 (Pewter/Black ) 5,517.86 1 5,517.86 IGST 662.14 6,180.00
HSN:8517
Amount in Words:
Six Thousand One Hundred And Eighty only
"""


def parse(text, etype=E.PURCHASE_INVOICE, hints=None):
    res = ExtractionResult([PageText(1, text)], ExtractionMethod.REGEX, 0.95)
    return {f.field_name: f for f in parse_document(res, etype, hints)}


def test_dotted_and_mixed_dates():
    assert parse_date("30.03.2018") == "2018-03-30"
    assert parse_date("30 Mar 2018") == "2018-03-30"
    assert parse_date("03/04/2026") is None            # ambiguous: never guessed
    assert parse_date("2026-02-30") is None            # impossible date


def test_words_to_number_and_refuses_garbage():
    assert words_to_number("Six Thousand One Hundred And Eighty only") == Decimal(6180)
    assert words_to_number("One Lakh Twenty Five Thousand only") == Decimal(125000)
    assert words_to_number("Sx Thousand only") is None


def test_label_in_middle_of_a_two_column_line():
    f = parse(MESSY)
    assert f[F.PURCHASE_DATE].normalized_value == "2018-03-30"


def test_amount_from_words_when_no_total_line_and_currency_from_gst():
    f = parse(MESSY)
    assert f[F.PURCHASE_AMOUNT].normalized_value == "6180.00" and f[F.CURRENCY].normalized_value == "INR"


def test_total_line_takes_rightmost_amount_and_agreeing_words_boost_confidence():
    f = parse(MESSY.replace("HSN:8517", "TOTAL: 662.14 6,180.00"))
    c = f[F.PURCHASE_AMOUNT].confidence   # None = "use the document default (0.95 for text/PDF)"
    assert f[F.PURCHASE_AMOUNT].normalized_value == "6180.00" and (c is None or c >= 0.8)


def test_numeric_total_disagreeing_with_words_forces_verification():
    f = parse(MESSY.replace("HSN:8517", "TOTAL: 662.14 7,180.00"))
    assert f[F.PURCHASE_AMOUNT].normalized_value == "7180.00" and f[F.PURCHASE_AMOUNT].confidence <= 0.5


def test_model_from_claim_hint_is_verified_in_document():
    f = parse(MESSY, hints=Hints(model="Nokia 2"))
    c = f[F.PRODUCT_MODEL].confidence
    assert f[F.PRODUCT_MODEL].raw_value == "Nokia 2" and (c is None or c >= 0.8)


def test_table_guess_is_capped_below_threshold():
    f = parse(MESSY)  # no hint -> heuristic from line-item table
    assert f[F.PRODUCT_MODEL].raw_value.startswith("Nokia 2") and f[F.PRODUCT_MODEL].confidence < settings.confidence_threshold


def test_hint_does_not_invent_a_model_that_is_not_in_the_document():
    f = parse(MESSY, hints=Hints(model="Galaxy S99"))
    assert "galaxy" not in (f[F.PRODUCT_MODEL].normalized_value if F.PRODUCT_MODEL in f else "")


def test_identifier_hint_must_literally_appear():
    assert F.DEVICE_IDENTIFIER not in parse(MESSY, hints=Hints(identifier="356938035643809"))
    f = parse(MESSY + "Handset 3569 3803 5643 809\n", hints=Hints(identifier="356938035643809"))
    assert f[F.DEVICE_IDENTIFIER].normalized_value == "356938035643809"


def test_parse_amount_picks_last_value():
    assert parse_amount("TOTAL: Rs. 662.14 Rs. 6,180.00") == ("6180.00", "INR")


def test_claimed_model_missing_from_readable_invoice_is_not_a_silent_pass(client):
    c = make_claim(client)   # claims "Northstar N14"
    upload(client, c["id"], b"Purchase Date: 2026-06-01\nSerial Number: NS-N14-000123\nTotal Amount: INR 100.00\n")
    ev = client.post(f"/api/v1/claims/{c['id']}/evaluate").json()
    rule = next(f for f in ev["findings"] if f["rule_id"].startswith("CON-001"))
    assert rule["result"] == "INDETERMINATE" and ev["recommendation"] == "MORE_INFORMATION_REQUIRED"


tesseract_missing = not Path(settings.tesseract_cmd).exists()


@pytest.mark.skipif(tesseract_missing, reason="Tesseract not installed")
def test_complex_marketplace_invoice_end_to_end(client):
    from app.demo.fixtures import ensure_fixtures
    img = (ensure_fixtures() / "complex_marketplace_invoice.png").read_bytes()
    c = make_claim(client, product_type="MOBILE_PHONE", claim_type="INSURANCE", policy_id="SYN-INS-PHONE-01",
                   product_brand="Aurora", product_model="A5", device_identifier="356938035643809",
                   event_type="ACCIDENTAL_DAMAGE", incident_date="2026-10-05", claimed_amount="5000.00")
    r = upload(client, c["id"], img, "invoice.png", mime="image/png")
    assert r.status_code == 201 and r.json()["extraction_status"] == "SUCCEEDED"
    facts = {f["field_name"]: f for f in r.json()["facts"]}
    assert facts["purchase_date"]["normalized_value"] == "2026-03-30"
    assert facts["purchase_amount"]["normalized_value"] == "24000.00" and facts["currency"]["normalized_value"] == "INR"
    ev = client.post(f"/api/v1/claims/{c['id']}/evaluate").json()
    by_rule = {f["rule_id"].split("_")[0]: f for f in ev["findings"]}
    assert by_rule["CON-001"]["result"] != "FAIL"            # a possible OCR misread never becomes a conflict
    assert ev["recommendation"] != "RECOMMENDED_REJECTION"
