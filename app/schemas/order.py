from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OrderStatusInput = Literal[
    "created",
    "paid",
    "accepted",
    "printing",
    "printed",
    "ready",
    "delivered",
    "failed",
    "cancelled",
]

PrintJobStatusInput = Literal["pending", "printing", "printed", "failed"]


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)
    extras: str = ""


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]


class OrderCreateResponse(BaseModel):
    order_id: int
    total: float
    status: str


class CashCheckoutResponse(BaseModel):
    order_id: int
    total: float
    status: str
    payment_method: str


class OrderStatusUpdate(BaseModel):
    status: OrderStatusInput


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    price: float
    extras: str | None = None


class PrintJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PrintJobStatusInput
    attempt_count: int
    max_attempts: int
    last_error: str | None = None
    locked_by: str | None = None
    created_at: datetime
    updated_at: datetime
    printed_at: datetime | None = None


class OrderAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_price: float
    items: list[OrderItemRead]
    print_jobs: list[PrintJobRead]


class PrintRequeueResponse(BaseModel):
    order_id: int
    print_job: PrintJobRead
