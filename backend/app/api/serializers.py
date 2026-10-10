"""Response shaping. Never exposes storage keys, token hashes or filesystem paths."""
from datetime import date, datetime

from app.db.models import (AuditEvent, Claim, Evaluation, Evidence, ExtractedFact, Finding, Policy, ReviewerDecision)


def ts(v: datetime | None) -> str | None:
    return v.isoformat() + "Z" if v else None


def d(v: date | None) -> str | None:
    return v.isoformat() if v else None


def policy_out(p: Policy) -> dict:
    return {"id": p.id, "policy_version": p.policy_version, "name": p.name, "product_type": p.product_type,
            "claim_type": p.claim_type, "valid_from": d(p.valid_from), "valid_to": d(p.valid_to),
            "coverage_days_from_purchase": p.coverage_days_from_purchase, "covered_event_types": p.covered_event_types,
            "excluded_event_types": p.excluded_event_types, "max_claim_amount": p.max_claim_amount,
            "deductible_amount": p.deductible_amount, "requires_purchase_proof": p.requires_purchase_proof,
            "requires_device_identifier": p.requires_device_identifier, "required_evidence_types": p.required_evidence_types,
            "requires_incident_description": p.requires_incident_description,
            "requires_repair_receipt_if_repaired": p.requires_repair_receipt_if_repaired,
            "cap_is_eligibility_ceiling": p.cap_is_eligibility_ceiling, "note": p.note, "source_label": p.source_label}


def claim_summary(c: Claim, rec: str | None = None) -> dict:
    return {"id": c.id, "claim_number": c.claim_number, "product_type": c.product_type, "product_brand": c.product_brand,
            "product_model": c.product_model, "claim_type": c.claim_type, "policy_id": c.policy_id, "status": c.status,
            "event_type": c.event_type, "submitted_at": ts(c.submitted_at), "latest_recommendation": rec,
            "claimed_amount": c.claimed_amount, "currency": c.currency}


def claim_out(c: Claim) -> dict:
    return {**claim_summary(c), "policy_version": c.policy_version, "device_identifier": c.device_identifier,
            "repair_already_performed": c.repair_already_performed, "incident_date": d(c.incident_date),
            "damage_or_failure_description": c.damage_or_failure_description, "created_at": ts(c.created_at),
            "updated_at": ts(c.updated_at)}


def fact_out(f: ExtractedFact) -> dict:
    return {"id": f.id, "evidence_id": f.evidence_id, "source": f.source, "field_name": f.field_name, "raw_value": f.raw_value,
            "normalized_value": f.normalized_value, "confidence": f.confidence, "source_page": f.source_page,
            "source_snippet": f.source_snippet, "extraction_method": f.extraction_method}


def evidence_out(e: Evidence, facts: list[ExtractedFact] | None = None) -> dict:
    out = {"id": e.id, "claim_id": e.claim_id, "evidence_type": e.evidence_type, "original_filename": e.original_filename,
           "mime_type": e.mime_type, "size_bytes": e.size_bytes, "sha256": e.sha256, "version_number": e.version_number,
           "uploaded_by": e.uploaded_by, "uploaded_at": ts(e.uploaded_at), "extraction_status": e.extraction_status,
           "extraction_error_code": e.extraction_error_code}
    if facts is not None:
        out["facts"] = [fact_out(f) for f in facts]
    return out


def finding_out(f: Finding) -> dict:
    return {"id": f.id, "rule_id": f.rule_id, "severity": f.severity, "result": f.result, "category": f.category,
            "title": f.title, "explanation": f.explanation, "field_name": f.field_name, "evidence_ids": f.evidence_ids,
            "source_fact_ids": f.source_fact_ids, "recommended_action": f.recommended_action, "reason_code": f.reason_code}


def evaluation_out(e: Evaluation) -> dict:
    return {"id": e.id, "claim_id": e.claim_id, "policy_id": e.policy_id, "policy_version": e.policy_version,
            "rules_version": e.rules_version, "recommendation": e.recommendation, "reason_codes": e.reason_codes,
            "missing_evidence": e.missing_evidence, "summary": e.summary, "ai_summary": e.ai_summary,
            "ai_provider": e.ai_provider, "started_at": ts(e.started_at), "completed_at": ts(e.completed_at),
            "processing_error_code": e.processing_error_code, "findings": [finding_out(f) for f in e.findings]}


def decision_out(x: ReviewerDecision) -> dict:
    return {"id": x.id, "evaluation_id": x.evaluation_id, "action": x.action, "reason": x.reason,
            "requested_items": x.requested_items, "reviewer_label": x.reviewer_label, "is_override": x.is_override,
            "created_at": ts(x.created_at)}


def audit_out(a: AuditEvent) -> dict:
    return {"id": a.id, "event_type": a.event_type, "actor_type": a.actor_type, "actor_label": a.actor_label,
            "details": a.details_json, "created_at": ts(a.created_at)}
