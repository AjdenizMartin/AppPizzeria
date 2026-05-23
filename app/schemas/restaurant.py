from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RestaurantSettingsPublic(BaseModel):
    model_config = ConfigDict(json_encoders={Decimal: lambda v: float(v)})

    restaurant_name: str
    public_phone: str
    whatsapp_number: str
    delivery_fee: Decimal
    minimum_order_amount: Decimal
    estimated_delivery_minutes: int
    is_accepting_orders: bool
    temporary_closed: bool = False
    temporary_closed_message: str | None = None
    banner_text: str | None = None


class RestaurantSettingsAdminRead(RestaurantSettingsPublic):
    address: str
    updated_at: datetime


class RestaurantSettingsUpdate(BaseModel):
    restaurant_name: str = Field(min_length=1, max_length=200)
    public_phone: str = Field(default="", max_length=50)
    whatsapp_number: str = Field(default="", max_length=50)
    address: str = Field(default="", max_length=500)
    delivery_fee: Decimal = Field(ge=0)
    minimum_order_amount: Decimal = Field(ge=0)
    estimated_delivery_minutes: int = Field(ge=1, le=240)
    is_accepting_orders: bool
    banner_text: str = Field(default="", max_length=500)
