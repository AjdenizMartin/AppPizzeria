from datetime import datetime
from decimal import Decimal
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
    extras: str = Field(default="", max_length=500)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]
    customer_name: str = Field(min_length=1, max_length=200)
    customer_email: str = Field(min_length=3, max_length=255)
    customer_phone: str = Field(min_length=3, max_length=30)
    delivery_address: str = Field(min_length=3, max_length=500)
    delivery_city: str = Field(min_length=2, max_length=100)
    delivery_postal_code: str = Field(min_length=2, max_length=20)
    delivery_notes: str = Field(default="", max_length=1000)
    payment_method: Literal["card", "cash"] = "card"
    delivery_fee: Decimal = Field(default=Decimal("2.50"), ge=0)


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
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    id: int
    product_id: int
    product_name: str
    quantity: int
    price: Decimal
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
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    id: int
    status: str
    customer_name: str
    customer_email: str | None = None
    customer_phone: str
    delivery_address: str
    delivery_city: str
    delivery_postal_code: str
    delivery_notes: str | None = None
    payment_method: str
    delivery_fee: Decimal
    total_price: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]
    print_jobs: list[PrintJobRead]


class OrderTrackingRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    id: int
    status: str
    customer_name: str
    customer_email: str | None = None
    customer_phone: str
    delivery_address: str
    delivery_city: str
    delivery_postal_code: str
    delivery_notes: str | None = None
    payment_method: str
    delivery_fee: Decimal
    total_price: Decimal
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]
    print_jobs: list[PrintJobRead]


class PrintRequeueResponse(BaseModel):
    order_id: int
    print_job: PrintJobRead
