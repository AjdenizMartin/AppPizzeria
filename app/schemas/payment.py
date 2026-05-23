from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    order_id: int


class CheckoutResponse(BaseModel):
    url: str
