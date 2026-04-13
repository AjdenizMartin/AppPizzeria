from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    price: float
    category: str
    image_url: str | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProductDeleteResponse(BaseModel):
    message: str
