from pydantic import BaseModel, Field


class OpeningHourRead(BaseModel):
    day_of_week: int
    opens_at: str
    closes_at: str
    is_closed: bool


class OpeningHourUpdate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    opens_at: str = Field(default="10:00")
    closes_at: str = Field(default="22:00")
    is_closed: bool = False


class RestaurantStatusRead(BaseModel):
    is_open: bool
    message: str
    estimated_delivery_minutes: int
    next_opening_time: str | None = None


class TemporaryClosureUpdate(BaseModel):
    temporary_closed: bool
    temporary_closed_message: str | None = None
