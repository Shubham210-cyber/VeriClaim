"""Claim lifecycle orchestration: creation, evidence ingestion, evaluation, decisions."""
import logging
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import get_provider, safe_summarize
from app.audit.service import record
from app.config import settings
from app.db.models import (AuditEvent, Claim, Evaluation, Evidence, ExtractedFact, Finding, Policy,
                           ReviewerDecision, UploadRequest, utcnow)
from app.documents import extract as extractor
from app.documents.storage import sanitize_filename, store_bytes, validate_upload
from app.enums import (ActorType, ClaimStatus, EvidenceType, ExtractionMethod, ExtractionStatus, FactSource,
                       FieldName, Recommendation, ReviewerAction, RuleResult, Uploader)
from app.errors import AppError
from app.normalization.parsers import normalize_identifier, normalize_model, parse_document
from app.rules.aggregator import Aggregate, aggregate, processing_failed
from app.rules.engine import (RULES_VERSION, ClaimView, Ctx, EvidenceView, FactView, PolicyView, RuleOutcome,
                              run_rules)
from app.uploads.tokens import create_token

log = logging.getLogger(__name__)
_TERMINAL = {ClaimStatus.APPROVED.value, ClaimStatus.REJECTED.value, ClaimStatus.CLOSED.value}


def _dec(v: str | None) -> Decimal | None:
    return Decimal(v) if v is not None else None


def get_claim(db: Session, claim_id: str) -> Claim:
    c = db.get(Claim, claim_id)
    if c is None:
        raise AppError(404, "NOT_FOUND", "Claim not found.")
    return c


def _next_number(db: Session) -> str:
    n = db.query(Claim).count() + 1
    while True:
        num = f"CP-{date.today().year}-{n:04d}"
        if not db.query(Claim).filter_by(claim_number=num).first():
            return num
        n += 1


def _claim_fact(claim_id: str, field: FieldName, raw: str, norm: str | None) -> ExtractedFact:
    return ExtractedFact(claim_id=claim_id, evidence_id=None, source=FactSource.CLAIM_RECORD.value, field_name=field.value,
                         raw_value=raw, normalized_value=norm, confidence=1.0, source_snippet="Claim record (entered by reviewer)",
                         extraction_method=ExtractionMethod.MANUAL.value)


def create_claim(db: Session, data: dict, claim_number: str | None = None) -> Claim:
    policy = db.get(Policy, (data["policy_id"], "1"))
    if policy is None:
        raise AppError(404, "POLICY_NOT_FOUND", "Selected policy does not exist.")
    claim = Claim(
        claim_number=claim_number or _next_number(db), policy_version=policy.policy_version,
        status=ClaimStatus.SUBMITTED.value, **{k: (v.value if hasattr(v, "value") else v) for k, v in data.items()},
    )
    if claim.claimed_amount is not None:
        claim.claimed_amount = str(Decimal(claim.claimed_amount))
    db.add(claim)
    db.flush()
    full_model = " ".join(x for x in (claim.product_brand, claim.product_model) if x)
    if full_model:
        db.add(_claim_fact(claim.id, FieldName.PRODUCT_MODEL, full_model, normalize_model(full_model)))
    if claim.device_identifier:
        db.add(_claim_fact(claim.id, FieldName.DEVICE_IDENTIFIER, claim.device_identifier, normalize_identifier(claim.device_identifier)))
    if claim.incident_date:
        db.add(_claim_fact(claim.id, FieldName.INCIDENT_DATE, claim.incident_date.isoformat(), claim.incident_date.isoformat()))
    if claim.claimed_amount is not None:
        db.add(_claim_fact(claim.id, FieldName.CLAIMED_AMOUNT, claim.claimed_amount, claim.claimed_amount))
        db.add(_claim_fact(claim.id, FieldName.CURRENCY, claim.currency, claim.currency))
    if claim.damage_or_failure_description or claim.event_type:
        db.add(_claim_fact(claim.id, FieldName.EVENT_DESCRIPTION,
                           claim.damage_or_failure_description or claim.event_type, claim.event_type))
    record(db, claim.id, "CLAIM_CREATED", ActorType.REVIEWER.value, details={"claim_number": claim.claim_number, "policy_id": claim.policy_id})
    db.commit()
    return claim


# ------------------------------------------------------------------ evidence
def ingest_evidence(db: Session, claim: Claim, filename: str, mime: str | None, data: bytes,
                    evidence_type: EvidenceType, uploaded_by: Uploader) -> Evidence:
    ext, canon_mime = validate_upload(filename, mime, data)  # raises 413/415 before anything is stored
    key, sha = store_bytes(data, ext)
    version = db.query(Evidence).filter_by(claim_id=claim.id, evidence_type=evidence_type.value).count() + 1
    ev = Evidence(claim_id=claim.id, evidence_type=evidence_type.value, original_filename=sanitize_filename(filename),
                  storage_key=key, mime_type=canon_mime, size_bytes=len(data), sha256=sha, version_number=version,
                  uploaded_by=uploaded_by.value, extraction_status=ExtractionStatus.PENDING.value)
    db.add(ev)
    db.flush()  # evidence row exists before extraction so failures stay visible
    try:
        res = extractor.extract(ext, data)
    except Exception:  # extraction is technical; never a claim outcome
        log.exception("extraction crashed for evidence %s", ev.id)
        res = extractor.ExtractionResult([], ExtractionMethod.REGEX, None, "EXTRACTION_ERROR")
    if res.error_code:
        ev.extraction_status, ev.extraction_error_code = ExtractionStatus.FAILED.value, res.error_code
    else:
        ev.extracted_text = res.text[:extractor.MAX_TEXT]
        parsed = parse_document(res, evidence_type)
        conf = res.confidence if res.confidence is not None else 0.5
        for p in parsed:
            db.add(ExtractedFact(claim_id=claim.id, evidence_id=ev.id, source=FactSource.DOCUMENT.value,
                                 field_name=p.field_name.value, raw_value=p.raw_value, normalized_value=p.normalized_value,
                                 confidence=conf, source_page=p.page, source_snippet=p.snippet[:300],
                                 extraction_method=res.method.value))
        if parsed:
            ev.extraction_status = ExtractionStatus.SUCCEEDED.value
        else:
            ev.extraction_status, ev.extraction_error_code = ExtractionStatus.PARTIAL.value, "NO_FIELDS_RECOGNIZED"
    record(db, claim.id, "EVIDENCE_UPLOADED", ActorType.CUSTOMER_LINK.value if uploaded_by == Uploader.CUSTOMER_LINK else ActorType.REVIEWER.value,
           details={"evidence_id": ev.id, "evidence_type": evidence_type.value, "version": version,
                    "extraction_status": ev.extraction_status, "filename": ev.original_filename})
    db.commit()
    return ev


# ---------------------------------------------------------------- evaluation
def _policy_view(p: Policy) -> PolicyView:
    return PolicyView(p.id, p.product_type, p.claim_type, p.valid_from, p.valid_to, p.coverage_days_from_purchase,
                      p.covered_event_types, p.excluded_event_types, _dec(p.max_claim_amount), _dec(p.deductible_amount),
                      p.requires_purchase_proof, p.requires_device_identifier, p.required_evidence_types,
                      p.requires_incident_description, p.requires_repair_receipt_if_repaired, p.cap_is_eligibility_ceiling)


def build_context(db: Session, claim: Claim, policy: Policy) -> tuple[Ctx, list[str]]:
    all_ev = db.scalars(select(Evidence).where(Evidence.claim_id == claim.id)).all()
    latest: dict[str, Evidence] = {}
    for e in all_ev:
        cur = latest.get(e.evidence_type)
        if cur is None or (e.version_number, e.uploaded_at) > (cur.version_number, cur.uploaded_at):
            latest[e.evidence_type] = e
    ev_views = []
    for e in latest.values():
        dup = db.query(Evidence).filter(Evidence.sha256 == e.sha256, Evidence.claim_id != claim.id).first() is not None
        ev_views.append(EvidenceView(e.id, e.evidence_type, e.extraction_status, e.sha256, dup))
    keep = {e.id: e for e in latest.values() if e.extraction_status != ExtractionStatus.FAILED.value}
    rows = db.scalars(select(ExtractedFact).where(ExtractedFact.claim_id == claim.id)).all()
    facts = []
    for f in rows:
        if f.source == FactSource.DOCUMENT.value and f.evidence_id not in keep:
            continue  # superseded or failed evidence versions are preserved but not evaluated
        etype = keep[f.evidence_id].evidence_type if f.evidence_id else None
        facts.append(FactView(f.id, f.field_name, f.raw_value, f.normalized_value, f.confidence, f.evidence_id, etype, f.source))
    cv = ClaimView(claim.product_type, claim.claim_type, claim.event_type, claim.repair_already_performed, claim.incident_date,
                   _dec(claim.claimed_amount), claim.currency, claim.damage_or_failure_description)
    return Ctx(cv, _policy_view(policy), ev_views, facts, settings.confidence_threshold), [f.id for f in facts]


def _persist(db: Session, ev: Evaluation, outcomes: list[RuleOutcome]) -> None:
    for o in outcomes:
        db.add(Finding(claim_id=ev.claim_id, evaluation_id=ev.id, rule_id=o.rule_id, severity=o.severity.value,
                       result=o.result.value, category=o.category.value, title=o.title, explanation=o.explanation,
                       field_name=o.field_name, evidence_ids=o.evidence_ids, source_fact_ids=[f.id for f in o.facts],
                       recommended_action=o.recommended_action, reason_code=o.reason_code))


def evaluate_claim(db: Session, claim: Claim, actor: ActorType = ActorType.REVIEWER, provider=None) -> Evaluation:
    started = utcnow()
    prev_status = claim.status
    policy = db.get(Policy, (claim.policy_id, claim.policy_version))
    ev = Evaluation(claim_id=claim.id, policy_id=claim.policy_id, policy_version=claim.policy_version,
                    rules_version=RULES_VERSION, recommendation=Recommendation.PROCESSING.value, started_at=started)
    db.add(ev)
    db.flush()
    outcomes: list[RuleOutcome] = []
    try:
        if policy is None:  # SYS-003: never invent coverage
            raise LookupError("POLICY_MISSING")
        ctx, fact_ids = build_context(db, claim, policy)
        outcomes = run_rules(ctx)
        agg: Aggregate = aggregate(outcomes)
        ev.fact_ids_used = fact_ids
        ai, label, degraded = safe_summarize(provider if provider is not None else get_provider(), {
            "recommendation": agg.recommendation.value,
            "claim": {"product_type": claim.product_type, "claim_type": claim.claim_type, "event_type": claim.event_type},
            "findings": [{"rule_id": o.rule_id, "title": o.title, "result": o.result.value, "category": o.category.value,
                          "explanation": o.explanation} for o in outcomes if o.result != RuleResult.NOT_APPLICABLE]})
        ev.ai_provider, ev.ai_summary = label, (ai.model_dump() if ai else None)
        if degraded:
            from app.enums import Category, Severity
            outcomes.append(RuleOutcome("SYS-002_AI_UNAVAILABLE", RuleResult.INDETERMINATE, Severity.INFO, "AI summary unavailable",
                                        "The AI provider was unavailable or returned invalid output; the deterministic summary is shown. "
                                        "Rule results and the recommendation are unaffected.", Category.NOTE, reason_code="AI_UNAVAILABLE"))
        ev.recommendation, ev.reason_codes = agg.recommendation.value, agg.reason_codes
        ev.missing_evidence, ev.summary = agg.missing_evidence, agg.summary
        _persist(db, ev, outcomes)
        ev.completed_at = utcnow()
        if prev_status not in _TERMINAL and prev_status != ClaimStatus.ESCALATED.value:
            claim.status = ClaimStatus.AWAITING_REVIEW.value
        record(db, claim.id, "EVALUATION_COMPLETED", actor.value,
               details={"evaluation_id": ev.id, "recommendation": ev.recommendation, "reason_codes": ev.reason_codes, "ai_provider": ev.ai_provider})
        db.commit()
    except Exception as exc:
        log.exception("evaluation failed for claim %s", claim.id)
        db.rollback()
        code = "POLICY_MISSING" if str(exc) == "POLICY_MISSING" else "EVALUATION_ERROR"
        failed = processing_failed(code)
        ev = Evaluation(claim_id=claim.id, policy_id=claim.policy_id, policy_version=claim.policy_version, rules_version=RULES_VERSION,
                        recommendation=failed.recommendation.value, reason_codes=failed.reason_codes, summary=failed.summary,
                        ai_provider="none", started_at=started, completed_at=utcnow(), processing_error_code=code)
        db.add(ev)
        c = db.get(Claim, claim.id)
        if c.status not in _TERMINAL:
            c.status = ClaimStatus.PROCESSING_FAILED.value
        record(db, claim.id, "EVALUATION_FAILED", ActorType.SYSTEM.value, details={"error_code": code})
        db.commit()
    return ev


def latest_evaluation(db: Session, claim_id: str) -> Evaluation | None:
    return db.scalars(select(Evaluation).where(Evaluation.claim_id == claim_id)
                      .order_by(Evaluation.started_at.desc(), Evaluation.id)).first()


# ----------------------------------------------------------------- decisions
_MATCH = {
    ReviewerAction.APPROVE: Recommendation.RECOMMENDED_APPROVAL,
    ReviewerAction.REJECT: Recommendation.RECOMMENDED_REJECTION,
    ReviewerAction.REQUEST_INFORMATION: Recommendation.MORE_INFORMATION_REQUIRED,
    ReviewerAction.ESCALATE: Recommendation.HUMAN_REVIEW_REQUIRED,
}
_TARGET = {
    ReviewerAction.APPROVE: ClaimStatus.APPROVED, ReviewerAction.REJECT: ClaimStatus.REJECTED,
    ReviewerAction.REQUEST_INFORMATION: ClaimStatus.AWAITING_CUSTOMER, ReviewerAction.ESCALATE: ClaimStatus.ESCALATED,
    ReviewerAction.MARK_UNDER_REVIEW: ClaimStatus.AWAITING_REVIEW,
}


def record_decision(db: Session, claim: Claim, evaluation_id: str, action: ReviewerAction, reason: str | None,
                    requested_items: list[dict], reviewer_label: str | None, expires_in_hours: int, max_uploads: int):
    ev = db.get(Evaluation, evaluation_id)
    if ev is None or ev.claim_id != claim.id:
        raise AppError(404, "EVALUATION_NOT_FOUND", "Evaluation does not belong to this claim.")
    latest = latest_evaluation(db, claim.id)
    if latest.id != ev.id:
        raise AppError(409, "STALE_EVALUATION", "A newer evaluation exists; review it before deciding.")
    if claim.status in _TERMINAL:
        raise AppError(400, "INVALID_STATE", f"Claim is already {claim.status}.")
    if action == ReviewerAction.APPROVE and ev.recommendation == Recommendation.PROCESSING_FAILED.value:
        raise AppError(400, "INVALID_STATE", "Cannot approve a claim whose evaluation failed; re-run the evaluation.")
    is_override = action in _MATCH and _MATCH[action].value != ev.recommendation
    if (action == ReviewerAction.REJECT or is_override) and not (reason or "").strip():
        raise AppError(422, "REASON_REQUIRED", "A reason is required for rejections and overrides.")
    if action == ReviewerAction.REQUEST_INFORMATION and not requested_items:
        raise AppError(422, "REQUESTED_ITEMS_REQUIRED", "At least one requested item is required.")
    d = ReviewerDecision(claim_id=claim.id, evaluation_id=ev.id, action=action.value, reason=reason,
                         requested_items=requested_items, reviewer_label=reviewer_label, is_override=is_override)
    db.add(d)
    claim.status = _TARGET[action].value
    token = None
    if action == ReviewerAction.REQUEST_INFORMATION:
        token, req = create_token(db, claim.id, requested_items, expires_in_hours, max_uploads)
        record(db, claim.id, "UPLOAD_LINK_CREATED", ActorType.REVIEWER.value, reviewer_label,
               {"upload_request_id": req.id, "expires_at": req.expires_at.isoformat(), "max_uploads": max_uploads})
    record(db, claim.id, "REVIEWER_DECISION", ActorType.REVIEWER.value, reviewer_label,
           {"action": action.value, "evaluation_id": ev.id, "recommendation": ev.recommendation,
            "is_override": is_override, "reason": reason})
    db.commit()
    return d, token
