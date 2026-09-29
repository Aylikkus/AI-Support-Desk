from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class TicketCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=200)
    customer_email: EmailStr
    message: str = Field(min_length=5, max_length=5000)


class Analysis(BaseModel):
    category: Category
    priority: Priority
    summary: str = Field(min_length=1)
    reply_draft: str = Field(min_length=1)


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
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime
