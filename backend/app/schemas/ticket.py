from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class Category(StrEnum):
    payment = "payment"
    technical = "technical"
    account = "account"
    delivery = "delivery"
    product = "product"
    other = "other"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TicketStatus(StrEnum):
    new = "new"
    pending_operator = "pending_operator"
    processed = "processed"
    failed = "failed"


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=200)
    customer_email: EmailStr
    message: str = Field(min_length=5, max_length=5000)


class Analysis(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(min_length=1)
    reply_draft: str = Field(min_length=1)


class TriageDecision(BaseModel):
    """Structured decision of the triage stage of the LangGraph support graph."""

    escalate: bool
    operator_question: str | None = Field(None, min_length=1)
    category: Category
    priority: Priority

    @model_validator(mode="after")
    def _question_required_when_escalating(self) -> "TriageDecision":
        if self.escalate and not self.operator_question:
            raise ValueError("operator_question is required when escalate is true")
        return self


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_email: str
    message: str
    category: Category | None
    priority: Priority | None
    summary: str | None
    reply_draft: str | None
    status: TicketStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class TicketCreated(TicketOut):
    """POST /api/tickets response; access_token is set only for escalated tickets."""

    access_token: str | None = None
