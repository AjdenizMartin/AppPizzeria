from pydantic import BaseModel, Field


class CheckoutItem(BaseModel):
    name: str
    price: float = Field(gt=0)
    quantity: int = Field(default=1, ge=1)


class CheckoutRequest(BaseModel):
    items: list[CheckoutItem]


class CheckoutResponse(BaseModel):
    url: str
