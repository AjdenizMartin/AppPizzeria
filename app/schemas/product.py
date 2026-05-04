from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(ge=0)
    category: str = Field(max_length=100)
    image_url: str | None = Field(default=None, max_length=500)


class ProductRead(ProductBase):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: lambda v: float(v)},
    )

    id: int


class ProductDeleteResponse(BaseModel):
    message: str
