"""Append-only audit log. There is intentionally no update/delete function."""
from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record(db: Session, claim_id: str, event_type: str, actor_type: str,
           actor_label: str | None = None, details: dict | None = None) -> AuditEvent:
    ev = AuditEvent(claim_id=claim_id, event_type=event_type, actor_type=actor_type,
                    actor_label=actor_label, details_json=details or {})
    db.add(ev)
    return ev
