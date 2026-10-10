from datetime import date, datetime, time as dtime

from fastapi import APIRouter, Depends, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api import serializers as ser
from app.api.schemas import ClaimCreate, DecisionCreate
from app.audit.service import record
from app.claims import service
from app.config import settings
from app.db.models import AuditEvent, Claim, Evaluation, Evidence, ExtractedFact, Policy, ReviewerDecision, UploadRequest, utcnow
from app.db.session import get_db
from app.documents.storage import path_for
from app.enums import ActorType, ClaimStatus, ClaimType, EvidenceType, FactSource, ProductType, Uploader
from app.errors import AppError
from app.uploads.tokens import resolve

router = APIRouter(prefix="/api/v1")


def _read_limited(file: UploadFile) -> bytes:
    data = file.file.read(settings.max_upload_bytes + 1)
    return data


# -------------------------------------------------------------- policies
@router.get("/policies")
def list_policies(db: Session = Depends(get_db)):
    return {"items": [ser.policy_out(p) for p in db.scalars(select(Policy).order_by(Policy.id))]}


@router.get("/policies/{policy_id}")
def get_policy(policy_id: str, db: Session = Depends(get_db)):
    p = db.scalars(select(Policy).where(Policy.id == policy_id).order_by(Policy.policy_version.desc())).first()
    if p is None:
        raise AppError(404, "NOT_FOUND", "Policy not found.")
    return ser.policy_out(p)


# ---------------------------------------------------------------- claims
@router.get("/claims")
def list_claims(status: ClaimStatus | None = None, product_type: ProductType | None = None, claim_type: ClaimType | None = None,
                q: str | None = Query(None, max_length=80), submitted_from: date | None = None, submitted_to: date | None = None,
                limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    stmt = select(Claim)
    if status:
        stmt = stmt.where(Claim.status == status.value)
    if product_type:
        stmt = stmt.where(Claim.product_type == product_type.value)
    if claim_type:
        stmt = stmt.where(Claim.claim_type == claim_type.value)
    if submitted_from:
        stmt = stmt.where(Claim.submitted_at >= datetime.combine(submitted_from, dtime.min))
    if submitted_to:
        stmt = stmt.where(Claim.submitted_at <= datetime.combine(submitted_to, dtime.max))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Claim.claim_number.ilike(like), Claim.product_model.ilike(like), Claim.product_brand.ilike(like)))
    total = len(db.scalars(stmt).all())
    rows = db.scalars(stmt.order_by(Claim.submitted_at.desc(), Claim.claim_number).limit(limit).offset(offset)).all()
    items = []
    for c in rows:
        ev = service.latest_evaluation(db, c.id)
        items.append(ser.claim_summary(c, ev.recommendation if ev else None))
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/claims", status_code=201)
def create_claim(body: ClaimCreate, db: Session = Depends(get_db)):
    c = service.create_claim(db, body.model_dump())
    return ser.claim_out(c)


@router.get("/claims/{claim_id}")
def claim_detail(claim_id: str, db: Session = Depends(get_db)):
    c = service.get_claim(db, claim_id)
    facts = db.scalars(select(ExtractedFact).where(ExtractedFact.claim_id == c.id).order_by(ExtractedFact.created_at)).all()
    by_ev: dict[str | None, list] = {}
    for f in facts:
        by_ev.setdefault(f.evidence_id, []).append(f)
    evidence = db.scalars(select(Evidence).where(Evidence.claim_id == c.id).order_by(Evidence.uploaded_at)).all()
    ev = service.latest_evaluation(db, c.id)
    decisions = db.scalars(select(ReviewerDecision).where(ReviewerDecision.claim_id == c.id).order_by(ReviewerDecision.created_at)).all()
    audit = db.scalars(select(AuditEvent).where(AuditEvent.claim_id == c.id).order_by(AuditEvent.created_at)).all()
    reqs = db.scalars(select(UploadRequest).where(UploadRequest.claim_id == c.id).order_by(UploadRequest.created_at)).all()
    return {
        "claim": ser.claim_out(c), "latest_evaluation": ser.evaluation_out(ev) if ev else None,
        "evidence": [ser.evidence_out(e, by_ev.get(e.id, [])) for e in evidence],
        "claim_record_facts": [ser.fact_out(f) for f in by_ev.get(None, [])],
        "decisions": [ser.decision_out(x) for x in decisions], "timeline": [ser.audit_out(a) for a in audit],
        "upload_requests": [{"id": r.id, "requested_items": r.requested_items, "expires_at": ser.ts(r.expires_at),
                             "revoked": r.revoked_at is not None, "remaining_uploads": r.max_uploads - r.upload_count} for r in reqs],
        "synthetic_notice": "Synthetic Hackathon Data - Not a Real Insurance Decision",
    }


@router.post("/claims/{claim_id}/evaluate")
def evaluate(claim_id: str, db: Session = Depends(get_db)):
    c = service.get_claim(db, claim_id)
    ev = service.evaluate_claim(db, c)
    db.refresh(ev)
    return {**ser.evaluation_out(ev), "claim_status": db.get(Claim, claim_id).status}


@router.get("/claims/{claim_id}/evaluations")
def evaluations(claim_id: str, db: Session = Depends(get_db)):
    service.get_claim(db, claim_id)
    rows = db.scalars(select(Evaluation).where(Evaluation.claim_id == claim_id).order_by(Evaluation.started_at.desc())).all()
    return {"items": [ser.evaluation_out(e) for e in rows]}


# -------------------------------------------------------------- evidence
@router.post("/claims/{claim_id}/evidence", status_code=201)
def upload_evidence(claim_id: str, file: UploadFile = File(...), evidence_type: EvidenceType = Form(...),
                    db: Session = Depends(get_db)):
    c = service.get_claim(db, claim_id)
    e = service.ingest_evidence(db, c, file.filename or "upload", file.content_type, _read_limited(file), evidence_type, Uploader.REVIEWER)
    facts = db.scalars(select(ExtractedFact).where(ExtractedFact.evidence_id == e.id)).all()
    return ser.evidence_out(e, facts)


def _evidence_or_404(db: Session, claim_id: str, evidence_id: str) -> Evidence:
    e = db.get(Evidence, evidence_id)
    if e is None or e.claim_id != claim_id:
        raise AppError(404, "NOT_FOUND", "Evidence not found.")
    return e


@router.get("/claims/{claim_id}/evidence/{evidence_id}")
def get_evidence(claim_id: str, evidence_id: str, db: Session = Depends(get_db)):
    e = _evidence_or_404(db, claim_id, evidence_id)
    return ser.evidence_out(e, db.scalars(select(ExtractedFact).where(ExtractedFact.evidence_id == e.id)).all())


@router.get("/claims/{claim_id}/evidence/{evidence_id}/download")
def download_evidence(claim_id: str, evidence_id: str, db: Session = Depends(get_db)):
    e = _evidence_or_404(db, claim_id, evidence_id)
    return FileResponse(path_for(e.storage_key), media_type=e.mime_type, filename=e.original_filename,
                        content_disposition_type="inline", headers={"X-Content-Type-Options": "nosniff"})


# ------------------------------------------------------------- decisions
@router.post("/claims/{claim_id}/decisions", status_code=201)
def decide(claim_id: str, body: DecisionCreate, db: Session = Depends(get_db)):
    c = service.get_claim(db, claim_id)
    d, token = service.record_decision(db, c, body.evaluation_id, body.action, body.reason,
                                       [i.model_dump(mode="json") for i in body.requested_items], body.reviewer_label,
                                       body.expires_in_hours, body.max_uploads)
    out = {"decision": ser.decision_out(d), "claim_status": c.status, "upload_link": None}
    if token:  # raw token is returned exactly once
        out["upload_link"] = {"token": token, "path": f"/customer-upload/{token}", "expires_in_hours": body.expires_in_hours}
    return out


@router.post("/claims/{claim_id}/upload-requests/{request_id}/revoke")
def revoke_upload_request(claim_id: str, request_id: str, db: Session = Depends(get_db)):
    r = db.get(UploadRequest, request_id)
    if r is None or r.claim_id != claim_id:
        raise AppError(404, "NOT_FOUND", "Upload request not found.")
    if r.revoked_at is None:
        r.revoked_at = utcnow()
        record(db, claim_id, "UPLOAD_LINK_REVOKED", ActorType.REVIEWER.value, details={"upload_request_id": r.id})
        db.commit()
    return {"id": r.id, "revoked": True}


@router.get("/claims/{claim_id}/audit")
def audit(claim_id: str, db: Session = Depends(get_db)):
    service.get_claim(db, claim_id)
    rows = db.scalars(select(AuditEvent).where(AuditEvent.claim_id == claim_id).order_by(AuditEvent.created_at)).all()
    return {"items": [ser.audit_out(a) for a in rows]}


# ---------------------------------------------------- public (token-scoped)
def _client(request: Request) -> str:
    return request.client.host if request.client else "?"


@router.get("/public/upload-request")
def public_request(request: Request, x_upload_token: str | None = Header(None), db: Session = Depends(get_db)):
    r = resolve(db, x_upload_token, _client(request))
    c = db.get(Claim, r.claim_id)
    return {"claim_reference": c.claim_number, "requested_items": r.requested_items, "expires_at": ser.ts(r.expires_at),
            "remaining_uploads": r.max_uploads - r.upload_count}


@router.post("/public/upload-request/evidence", status_code=201)
def public_upload(request: Request, file: UploadFile = File(...), evidence_type: EvidenceType = Form(...),
                  x_upload_token: str | None = Header(None), db: Session = Depends(get_db)):
    r = resolve(db, x_upload_token, _client(request), for_upload=True)
    allowed = {i["item_type"] for i in r.requested_items} | {EvidenceType.OTHER.value}
    if evidence_type.value not in allowed:
        raise AppError(422, "TYPE_NOT_REQUESTED", "This document type was not requested.")
    c = db.get(Claim, r.claim_id)
    e = service.ingest_evidence(db, c, file.filename or "upload", file.content_type, _read_limited(file), evidence_type, Uploader.CUSTOMER_LINK)
    r.upload_count += 1
    record(db, c.id, "CUSTOMER_UPLOAD_ACCEPTED", ActorType.CUSTOMER_LINK.value, details={"upload_request_id": r.id, "evidence_id": e.id})
    if c.status == ClaimStatus.AWAITING_CUSTOMER.value:
        c.status = ClaimStatus.AWAITING_REVIEW.value
    db.commit()
    service.evaluate_claim(db, c, ActorType.CUSTOMER_LINK)  # reprocess; result is reviewer-only
    return {"status": "received", "extraction_status": e.extraction_status, "remaining_uploads": r.max_uploads - r.upload_count}


# ------------------------------------------------------------------ demo
@router.post("/demo/seed")
def demo_seed(db: Session = Depends(get_db)):
    """One-click seeded demo claims (synthetic data). Idempotent."""
    from app.demo.seed import seed_demo
    return {"created": seed_demo(db)}
