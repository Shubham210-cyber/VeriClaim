"""SQLAlchemy models. Money is stored as TEXT (Decimal strings); datetimes are naive UTC."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    policy_version: Mapped[str] = mapped_column(String, primary_key=True, default="1")
    name: Mapped[str] = mapped_column(String)
    product_type: Mapped[str] = mapped_column(String)
    claim_type: Mapped[str] = mapped_column(String)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    coverage_days_from_purchase: Mapped[int | None] = mapped_column(Integer, nullable=True)
    covered_event_types: Mapped[list] = mapped_column(JSON)
    excluded_event_types: Mapped[list] = mapped_column(JSON)
    max_claim_amount: Mapped[str | None] = mapped_column(String, nullable=True)
    deductible_amount: Mapped[str | None] = mapped_column(String, nullable=True)
    requires_purchase_proof: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_device_identifier: Mapped[bool] = mapped_column(Boolean, default=True)
    required_evidence_types: Mapped[list] = mapped_column(JSON)
    requires_incident_description: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_repair_receipt_if_repaired: Mapped[bool] = mapped_column(Boolean, default=False)
    cap_is_eligibility_ceiling: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    source_label: Mapped[str] = mapped_column(String, default="STANDARD")


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_number: Mapped[str] = mapped_column(String, unique=True, index=True)
    product_type: Mapped[str] = mapped_column(String)
    product_brand: Mapped[str | None] = mapped_column(String, nullable=True)
    product_model: Mapped[str | None] = mapped_column(String, nullable=True)
    device_identifier: Mapped[str | None] = mapped_column(String, nullable=True)
    claim_type: Mapped[str] = mapped_column(String)
    policy_id: Mapped[str] = mapped_column(String, index=True)
    policy_version: Mapped[str] = mapped_column(String, default="1")
    event_type: Mapped[str | None] = mapped_column(String, nullable=True)
    repair_already_performed: Mapped[bool] = mapped_column(Boolean, default=False)
    incident_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    claimed_amount: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="INR")
    damage_or_failure_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="SUBMITTED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(["policy_id", "policy_version"], ["policies.id", "policies.policy_version"]),
    )

    evidence: Mapped[list["Evidence"]] = relationship(back_populates="claim", order_by="Evidence.uploaded_at")


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String)
    original_filename: Mapped[str] = mapped_column(String)
    storage_key: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    uploaded_by: Mapped[str] = mapped_column(String)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    extraction_status: Mapped[str] = mapped_column(String, default="PENDING")
    extraction_error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # bounded excerpt
    claim: Mapped[Claim] = relationship(back_populates="evidence")
    facts: Mapped[list["ExtractedFact"]] = relationship(back_populates="evidence_row")


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String, default="DOCUMENT")
    field_name: Mapped[str] = mapped_column(String)
    raw_value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    evidence_row: Mapped[Evidence | None] = relationship(back_populates="facts")


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    policy_id: Mapped[str] = mapped_column(String)
    policy_version: Mapped[str] = mapped_column(String)
    rules_version: Mapped[str] = mapped_column(String)
    recommendation: Mapped[str] = mapped_column(String)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    missing_evidence: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    ai_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_provider: Mapped[str] = mapped_column(String, default="none")
    fact_ids_used: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    findings: Mapped[list["Finding"]] = relationship(back_populates="evaluation", order_by="Finding.created_at")


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id"), index=True)
    rule_id: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    result: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, default="NONE")
    title: Mapped[str] = mapped_column(String)
    explanation: Mapped[str] = mapped_column(Text)
    field_name: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    source_fact_ids: Mapped[list] = mapped_column(JSON, default=list)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    evaluation: Mapped[Evaluation] = relationship(back_populates="findings")


class ReviewerDecision(Base):
    __tablename__ = "reviewer_decisions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id"))
    action: Mapped[str] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_items: Mapped[list] = mapped_column(JSON, default=list)
    reviewer_label: Mapped[str | None] = mapped_column(String, nullable=True)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UploadRequest(Base):
    __tablename__ = "upload_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    requested_items: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    max_uploads: Mapped[int] = mapped_column(Integer, default=5)
    upload_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    event_type: Mapped[str] = mapped_column(String)
    actor_type: Mapped[str] = mapped_column(String)
    actor_label: Mapped[str | None] = mapped_column(String, nullable=True)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
