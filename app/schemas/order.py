from pydantic import BaseModel
from typing import List, Optional


class OrderItemCreate(BaseModel):
    product_id: int
    size_id: Optional[int] = None
    quantity: int
    extras: List[int] = []