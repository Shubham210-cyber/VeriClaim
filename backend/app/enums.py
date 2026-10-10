"""Single definition of every enum (see docs/DATA_MODELS.md and DECISIONS.md)."""
from enum import Enum


class _S(str, Enum):
    def __str__(self) -> str:  # serialise as plain value
        return self.value


class ProductType(_S):
    LAPTOP = "LAPTOP"
    MOBILE_PHONE = "MOBILE_PHONE"


class ClaimType(_S):
    WARRANTY = "WARRANTY"
    INSURANCE = "INSURANCE"


class EventType(_S):
    MANUFACTURING_DEFECT = "MANUFACTURING_DEFECT"
    HARDWARE_FAILURE = "HARDWARE_FAILURE"
    ACCIDENTAL_DAMAGE = "ACCIDENTAL_DAMAGE"
    LIQUID_DAMAGE = "LIQUID_DAMAGE"
    THEFT = "THEFT"
    COSMETIC_WEAR = "COSMETIC_WEAR"
    OTHER = "OTHER"


class ClaimStatus(_S):
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    AWAITING_CUSTOMER = "AWAITING_CUSTOMER"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    PROCESSING_FAILED = "PROCESSING_FAILED"


class Recommendation(_S):
    RECOMMENDED_APPROVAL = "RECOMMENDED_APPROVAL"
    RECOMMENDED_REJECTION = "RECOMMENDED_REJECTION"
    MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PROCESSING = "PROCESSING"
    PROCESSING_FAILED = "PROCESSING_FAILED"


class ReviewerAction(_S):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    ESCALATE = "ESCALATE"
    MARK_UNDER_REVIEW = "MARK_UNDER_REVIEW"


class RuleResult(_S):
    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Severity(_S):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceType(_S):
    CLAIM_FORM = "CLAIM_FORM"
    PURCHASE_INVOICE = "PURCHASE_INVOICE"
    POLICY_DOCUMENT = "POLICY_DOCUMENT"
    WARRANTY_DOCUMENT = "WARRANTY_DOCUMENT"
    REPAIR_RECEIPT = "REPAIR_RECEIPT"
    CUSTOMER_STATEMENT = "CUSTOMER_STATEMENT"
    OTHER = "OTHER"


class ExtractionStatus(_S):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class FieldName(_S):
    PRODUCT_MODEL = "product_model"
    DEVICE_IDENTIFIER = "device_identifier"
    PURCHASE_DATE = "purchase_date"
    INCIDENT_DATE = "incident_date"
    REPAIR_DATE = "repair_date"
    PURCHASE_AMOUNT = "purchase_amount"
    REPAIR_AMOUNT = "repair_amount"
    CLAIMED_AMOUNT = "claimed_amount"
    CURRENCY = "currency"
    EVENT_DESCRIPTION = "event_description"


class FactSource(_S):
    DOCUMENT = "DOCUMENT"
    CLAIM_RECORD = "CLAIM_RECORD"


class ExtractionMethod(_S):
    REGEX = "REGEX"
    OCR = "OCR"
    AI = "AI"
    MANUAL = "MANUAL"


class Uploader(_S):
    REVIEWER = "REVIEWER"
    CUSTOMER_LINK = "CUSTOMER_LINK"


class ActorType(_S):
    SYSTEM = "SYSTEM"
    REVIEWER = "REVIEWER"
    CUSTOMER_LINK = "CUSTOMER_LINK"


class Category(_S):
    """Rule-outcome class used by the recommendation aggregator."""
    CONFLICT = "CONFLICT"                      # material contradiction -> human review
    AMBIGUOUS = "AMBIGUOUS"                    # classification unclear -> human review
    REJECTION_CANDIDATE = "REJECTION_CANDIDATE"
    MISSING = "MISSING"                        # evidence/field to request
    CLARIFY = "CLARIFY"                        # needs verification/clarification
    NOTE = "NOTE"                              # informational, never blocks
    NONE = "NONE"
