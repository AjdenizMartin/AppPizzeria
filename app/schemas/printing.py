from datetime import datetime

from pydantic import BaseModel, Field


class PrintAgentPullRequest(BaseModel):
    agent_id: str = Field(min_length=2, max_length=120)


class PrintAgentJobItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float
    extras: str = ""


class PrintAgentJobOrder(BaseModel):
    id: int
    daily_order_number: int
    status: str
    customer_name: str
    customer_email: str | None = None
    customer_phone: str
    delivery_address: str
    delivery_city: str
    delivery_postal_code: str
    delivery_notes: str | None = None
    payment_method: str
    subtotal: float
    delivery_fee: float
    total_price: float
    created_at: datetime
    items: list[PrintAgentJobItem]


class PrintAgentJobEnvelope(BaseModel):
    job_id: int
    attempt_count: int
    max_attempts: int
    order: PrintAgentJobOrder


class PrintAgentPullResponse(BaseModel):
    job: PrintAgentJobEnvelope | None


class PrintAgentJobResolveRequest(BaseModel):
    agent_id: str = Field(min_length=2, max_length=120)


class PrintAgentJobFailRequest(PrintAgentJobResolveRequest):
    error: str = Field(min_length=3, max_length=500)
