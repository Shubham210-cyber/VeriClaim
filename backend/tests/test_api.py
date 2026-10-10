import re
import shutil
from pathlib import Path

import pytest

from app.ai.provider import AiUnavailable, safe_summarize
from app.config import settings
from app.db.models import AuditEvent, Evaluation, Evidence, UploadRequest
from tests.conftest import INVOICE, make_claim, upload

H = "/api/v1"


def evaluate(client, cid):
    r = client.post(f"{H}/claims/{cid}/evaluate")
    assert r.status_code == 200, r.text
    return r.json()


def test_health_and_no_secret_leak(client):
    r = client.get("/health")
    assert r.json() == {"status": "ok", "ai_provider": "mock"}


def test_create_upload_evaluate_view_findings(client):
    c = make_claim(client)
    up = upload(client, c["id"])
    assert up.status_code == 201
    body = up.json()
    assert body["extraction_status"] == "SUCCEEDED" and "storage_key" not in body
    assert {f["field_name"] for f in body["facts"]} >= {"purchase_date", "device_identifier", "product_model"}
    ev = evaluate(client, c["id"])
    assert ev["recommendation"] == "RECOMMENDED_APPROVAL" and ev["ai_provider"] == "mock"
    detail = client.get(f"{H}/claims/{c['id']}").json()
    assert detail["claim"]["status"] == "AWAITING_REVIEW"
    assert detail["latest_evaluation"]["findings"] and "storage_key" not in str(detail)


def test_reevaluation_creates_new_evaluation_and_keeps_old(client, db):
    c = make_claim(client)
    e1 = evaluate(client, c["id"])
    assert e1["recommendation"] == "MORE_INFORMATION_REQUIRED"
    upload(client, c["id"])
    e2 = evaluate(client, c["id"])
    assert e2["id"] != e1["id"] and e2["recommendation"] == "RECOMMENDED_APPROVAL"
    items = client.get(f"{H}/claims/{c['id']}/evaluations").json()["items"]
    assert [i["id"] for i in items][0] == e2["id"] and e1["id"] in {i["id"] for i in items}
    assert db.query(Evaluation).filter_by(claim_id=c["id"]).count() == 2


@pytest.mark.parametrize("name,data,mime,code", [
    ("x.exe", b"MZ....", "application/octet-stream", 415),
    ("x.png", b"not a png", "image/png", 415),
    ("x.txt", b"ok", "image/png", 415),
    ("../../evil.txt", b"\x00\x01binary", "text/plain", 415),
])
def test_unsupported_uploads(client, name, data, mime, code):
    c = make_claim(client)
    assert upload(client, c["id"], data, name, mime=mime).status_code == code


def test_oversized_upload_413(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    c = make_claim(client)
    r = upload(client, c["id"], b"a" * 500)
    assert r.status_code == 413 and r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_storage_key_independent_of_filename_and_traversal_safe(client, db):
    c = make_claim(client)
    r = upload(client, c["id"], INVOICE, "..\\..\\secret name.txt")
    assert r.status_code == 201
    e = db.query(Evidence).one()
    assert re.fullmatch(r"[0-9a-f]{32}\.txt", e.storage_key) and ".." not in e.original_filename and "/" not in e.original_filename
    assert (Path(settings.storage_dir) / e.storage_key).exists()


def test_corrupt_image_fails_extraction_but_is_not_a_rejection(client):
    c = make_claim(client)
    png = b"\x89PNG\r\n\x1a\n" + b"garbage"
    r = upload(client, c["id"], png, "bad.png", mime="image/png")
    assert r.status_code == 201 and r.json()["extraction_status"] == "FAILED"
    ev = evaluate(client, c["id"])
    assert ev["recommendation"] != "RECOMMENDED_REJECTION"


def test_unknown_and_invalid(client):
    assert client.get(f"{H}/claims/nope").status_code == 404
    assert client.get(f"{H}/claims/nope/evidence/x").status_code == 404
    r = client.post(f"{H}/claims", json={"product_type": "TOASTER"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_evidence_download_scoped_to_claim(client):
    a, b = make_claim(client), make_claim(client)
    eid = upload(client, a["id"]).json()["id"]
    assert client.get(f"{H}/claims/{a['id']}/evidence/{eid}/download").status_code == 200
    assert client.get(f"{H}/claims/{b['id']}/evidence/{eid}/download").status_code == 404


def test_filters_and_pagination(client):
    make_claim(client)
    make_claim(client, product_type="MOBILE_PHONE", claim_type="INSURANCE", policy_id="SYN-INS-PHONE-01", product_model="A5")
    assert client.get(f"{H}/claims?product_type=MOBILE_PHONE").json()["total"] == 1
    assert client.get(f"{H}/claims?q=A5").json()["total"] == 1
    assert client.get(f"{H}/claims?limit=1").json()["items"].__len__() == 1
    assert client.get(f"{H}/claims?limit=1000").status_code == 422


# ------------------------------------------------------------- decisions
def _decide(client, cid, eid, action, **kw):
    return client.post(f"{H}/claims/{cid}/decisions", json={"evaluation_id": eid, "action": action, **kw})


def test_decision_validation_and_audit(client, db):
    c = make_claim(client)
    upload(client, c["id"])
    ev = evaluate(client, c["id"])
    assert _decide(client, c["id"], ev["id"], "REJECT").status_code == 422          # needs reason
    assert _decide(client, c["id"], ev["id"], "REQUEST_INFORMATION").status_code == 422  # needs items
    assert _decide(client, c["id"], "bogus", "APPROVE").status_code == 404
    r = _decide(client, c["id"], ev["id"], "APPROVE")
    assert r.status_code == 201 and r.json()["claim_status"] == "APPROVED" and r.json()["decision"]["is_override"] is False
    assert _decide(client, c["id"], ev["id"], "APPROVE").status_code == 400           # terminal
    assert db.query(AuditEvent).filter_by(event_type="REVIEWER_DECISION").count() == 1


def test_override_requires_reason_and_stale_evaluation_rejected(client):
    c = make_claim(client)
    ev1 = evaluate(client, c["id"])       # MORE_INFORMATION_REQUIRED
    assert _decide(client, c["id"], ev1["id"], "APPROVE").status_code == 422   # override w/o reason
    ev2 = evaluate(client, c["id"])
    assert _decide(client, c["id"], ev1["id"], "ESCALATE", reason="x").status_code == 409
    r = _decide(client, c["id"], ev2["id"], "APPROVE", reason="Documents verified offline")
    assert r.status_code == 201 and r.json()["decision"]["is_override"] is True


def test_audit_endpoint_has_no_secrets(client):
    c = make_claim(client)
    tok = _link(client, c["id"])
    text = client.get(f"{H}/claims/{c['id']}/audit").text + client.get(f"{H}/claims/{c['id']}").text
    from app.uploads.tokens import hash_token
    assert tok not in text and hash_token(tok) not in text and "UPLOAD_LINK_CREATED" in text


# ------------------------------------------------------ customer upload
def _link(client, cid, **kw):
    ev = evaluate(client, cid)
    r = _decide(client, cid, ev["id"], "REQUEST_INFORMATION",
                requested_items=[{"item_type": "PURCHASE_INVOICE", "description": "Upload a readable invoice"}], **kw)
    assert r.status_code == 201, r.text
    assert r.json()["claim_status"] == "AWAITING_CUSTOMER"
    return r.json()["upload_link"]["token"]


def test_full_customer_resubmission_flow(client, db):
    c = make_claim(client)
    tok = _link(client, c["id"])
    assert db.query(UploadRequest).one().token_hash != tok            # only hash stored
    info = client.get(f"{H}/public/upload-request", headers={"X-Upload-Token": tok}).json()
    assert set(info) == {"claim_reference", "requested_items", "expires_at", "remaining_uploads"}
    r = client.post(f"{H}/public/upload-request/evidence", headers={"X-Upload-Token": tok},
                    files={"file": ("inv.txt", INVOICE, "text/plain")}, data={"evidence_type": "PURCHASE_INVOICE"})
    assert r.status_code == 201 and set(r.json()) == {"status", "extraction_status", "remaining_uploads"}
    d = client.get(f"{H}/claims/{c['id']}").json()
    assert d["claim"]["status"] == "AWAITING_REVIEW" and d["latest_evaluation"]["recommendation"] == "RECOMMENDED_APPROVAL"
    assert len(client.get(f"{H}/claims/{c['id']}/evaluations").json()["items"]) == 2
    types = [t["event_type"] for t in d["timeline"]]
    assert "UPLOAD_LINK_CREATED" in types and "CUSTOMER_UPLOAD_ACCEPTED" in types


def test_token_failures(client, db):
    c = make_claim(client)
    tok = _link(client, c["id"])
    hdr = lambda t: {"X-Upload-Token": t}
    assert client.get(f"{H}/public/upload-request", headers=hdr("nope")).status_code == 404
    assert client.get(f"{H}/public/upload-request").status_code == 404
    # wrong evidence type not requested
    r = client.post(f"{H}/public/upload-request/evidence", headers=hdr(tok), files={"file": ("a.txt", b"x", "text/plain")},
                    data={"evidence_type": "REPAIR_RECEIPT"})
    assert r.status_code == 422
    # revoke
    rid = client.get(f"{H}/claims/{c['id']}").json()["upload_requests"][0]["id"]
    assert client.post(f"{H}/claims/{c['id']}/upload-requests/{rid}/revoke").status_code == 200
    assert client.get(f"{H}/public/upload-request", headers=hdr(tok)).json()["error"]["code"] == "LINK_REVOKED"


def test_expired_and_exhausted_tokens(client, db):
    from datetime import timedelta
    from app.db.models import utcnow
    c = make_claim(client)
    tok = _link(client, c["id"], max_uploads=1)
    h = {"X-Upload-Token": tok}
    f = lambda: client.post(f"{H}/public/upload-request/evidence", headers=h, files={"file": ("a.txt", INVOICE, "text/plain")},
                            data={"evidence_type": "PURCHASE_INVOICE"})
    assert f().status_code == 201
    assert f().status_code == 403 and f().json()["error"]["code"] == "LINK_EXHAUSTED"
    r = db.query(UploadRequest).one()
    r.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert client.get(f"{H}/public/upload-request", headers=h).json()["error"]["code"] == "LINK_EXPIRED"


def test_token_cannot_reach_reviewer_endpoints(client):
    c = make_claim(client)
    tok = _link(client, c["id"])
    text = client.get(f"{H}/public/upload-request", headers={"X-Upload-Token": tok}).text
    for leaked in ("findings", "recommendation", c["id"], "policy", "evidence"):
        assert leaked not in text
    # the token header alone never authorises reviewer routes' data for other claims
    other = make_claim(client)
    r = client.post(f"{H}/public/upload-request/evidence", headers={"X-Upload-Token": tok},
                    files={"file": ("a.txt", INVOICE, "text/plain")}, data={"evidence_type": "PURCHASE_INVOICE"})
    assert r.status_code == 201
    assert client.get(f"{H}/claims/{other['id']}").json()["evidence"] == []


# ------------------------------------------------------------------- AI
def test_ai_failure_falls_back_without_changing_result(client, monkeypatch):
    c = make_claim(client)
    upload(client, c["id"])
    baseline = evaluate(client, c["id"])

    class Boom:
        name = "sonnet"

        def summarize_findings(self, payload):
            raise AiUnavailable("down")

    monkeypatch.setattr("app.claims.service.get_provider", lambda: Boom())
    degraded = evaluate(client, c["id"])
    assert degraded["recommendation"] == baseline["recommendation"] and degraded["ai_summary"] is None
    assert any(f["rule_id"] == "SYS-002_AI_UNAVAILABLE" for f in degraded["findings"])
    strip = lambda e: [(f["rule_id"], f["result"]) for f in e["findings"] if f["rule_id"].startswith(("POL", "EV", "CON"))]
    assert strip(degraded) == strip(baseline)


def test_malformed_ai_json_is_dropped():
    class Bad:
        name = "sonnet"

        def summarize_findings(self, payload):
            from app.ai.provider import AiSummary
            return AiSummary.model_validate_json("{not json")

    s, label, degraded = safe_summarize(Bad(), {"findings": []})
    assert s is None and degraded is True


def test_invented_citations_are_removed():
    from app.ai.provider import AiSummary

    class Cites:
        name = "sonnet"

        def summarize_findings(self, payload):
            return AiSummary(summary="ok", cited_rule_ids=["EV-001_REQUIRED_PURCHASE_PROOF", "MADE-UP"])

    s, _, _ = safe_summarize(Cites(), {"findings": [{"rule_id": "EV-001_REQUIRED_PURCHASE_PROOF"}]})
    assert s.cited_rule_ids == ["EV-001_REQUIRED_PURCHASE_PROOF"]


# ------------------------------------------------------- demo (real OCR)
tesseract_missing = not Path(settings.tesseract_cmd).exists()


@pytest.mark.skipif(tesseract_missing, reason="Tesseract not installed")
def test_demo_scenarios_with_real_ocr(client, db):
    from app.demo.seed import seed_demo
    assert len(seed_demo(db)) == 4 and seed_demo(db) == []   # idempotent
    expected = {"CP-DEMO-001": "RECOMMENDED_APPROVAL", "CP-DEMO-002": "MORE_INFORMATION_REQUIRED",
                "CP-DEMO-003": "RECOMMENDED_REJECTION", "CP-DEMO-004": "HUMAN_REVIEW_REQUIRED"}
    items = client.get(f"{H}/claims").json()["items"]
    assert {i["claim_number"]: i["latest_recommendation"] for i in items} == expected
    d4 = next(i for i in items if i["claim_number"] == "CP-DEMO-004")
    detail = client.get(f"{H}/claims/{d4['id']}").json()
    f = next(x for x in detail["latest_evaluation"]["findings"] if x["rule_id"].startswith("CON-005"))
    assert f["evidence_ids"] and f["source_fact_ids"] and "fraud" in f["explanation"].lower()
