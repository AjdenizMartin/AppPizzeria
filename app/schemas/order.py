from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)
    extras: str = ""


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]


class OrderCreateResponse(BaseModel):
    order_id: int
    total: float
