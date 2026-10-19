from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ticket import TicketOut


class OperatorRequestStatus(StrEnum):
    pending = "pending"
    answered = "answered"
    cancelled = "cancelled"


class OperatorAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)


class OperatorRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    question: str
    answer: str | None
    status: OperatorRequestStatus
    created_at: datetime
    answered_at: datetime | None


class OperatorRequestDetail(OperatorRequestOut):
    ticket: TicketOut
