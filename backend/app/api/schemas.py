from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.enums import ClaimType, EventType, EvidenceType, ProductType, ReviewerAction


class ClaimCreate(BaseModel):
    product_type: ProductType
    product_brand: str | None = Field(None, max_length=80)
    product_model: str | None = Field(None, max_length=80)
    device_identifier: str | None = Field(None, max_length=64)
    claim_type: ClaimType
    policy_id: str
    event_type: EventType | None = None
    repair_already_performed: bool = False
    incident_date: date | None = None
    claimed_amount: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    currency: str = Field("INR", min_length=3, max_length=3)
    damage_or_failure_description: str | None = Field(None, max_length=2000)


class RequestedItem(BaseModel):
    item_type: EvidenceType
    description: str = Field(min_length=1, max_length=500)


class DecisionCreate(BaseModel):
    evaluation_id: str
    action: ReviewerAction
    reason: str | None = Field(None, max_length=2000)
    requested_items: list[RequestedItem] = Field(default_factory=list, max_length=10)
    reviewer_label: str | None = Field(None, max_length=60)
    expires_in_hours: int = Field(72, ge=1, le=72)
    max_uploads: int = Field(5, ge=1, le=10)
