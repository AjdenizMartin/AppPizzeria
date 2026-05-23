from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import models

DEFAULTS = {
    "restaurant_name": "Pizzeria",
    "public_phone": "",
    "whatsapp_number": "",
    "address": "",
    "delivery_fee": Decimal("2.50"),
    "minimum_order_amount": Decimal("0"),
    "estimated_delivery_minutes": 35,
    "is_accepting_orders": True,
    "temporary_closed": False,
    "temporary_closed_message": "",
    "banner_text": "",
}


def get_or_create_settings(db: Session) -> models.RestaurantSettings:
    settings = db.get(models.RestaurantSettings, 1)
    if settings is None:
        settings = models.RestaurantSettings(id=1, **DEFAULTS)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, *, payload: dict) -> models.RestaurantSettings:
    settings = get_or_create_settings(db)
    for key, value in payload.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


def list_opening_hours(db: Session) -> list[models.OpeningHour]:
    rows = (
        db.query(models.OpeningHour).order_by(models.OpeningHour.day_of_week.asc()).all()
    )
    if rows:
        return rows
    defaults = []
    for day in range(7):
        defaults.append(
            models.OpeningHour(
                day_of_week=day,
                opens_at="10:00",
                closes_at="22:00",
                is_closed=False,
            )
        )
    db.add_all(defaults)
    db.commit()
    return (
        db.query(models.OpeningHour).order_by(models.OpeningHour.day_of_week.asc()).all()
    )


def replace_opening_hours(db: Session, *, payload: list[dict]) -> list[models.OpeningHour]:
    db.query(models.OpeningHour).delete()
    db.add_all([models.OpeningHour(**row) for row in payload])
    db.commit()
    return list_opening_hours(db)


def is_restaurant_open(db: Session, *, now: datetime | None = None) -> dict:
    settings = get_or_create_settings(db)
    if settings.temporary_closed:
        return {
            "is_open": False,
            "message": settings.temporary_closed_message or "Temporarily closed",
            "next_opening_time": None,
        }
    if not settings.is_accepting_orders:
        return {
            "is_open": False,
            "message": "Restaurant is not accepting orders",
            "next_opening_time": None,
        }
    current = now or datetime.now()
    day = current.weekday()
    hm = current.strftime("%H:%M")
    rows = list_opening_hours(db)
    row = next((r for r in rows if r.day_of_week == day), None)
    if row is None or row.is_closed:
        return {"is_open": False, "message": "Closed now", "next_opening_time": None}
    if row.opens_at <= hm <= row.closes_at:
        return {"is_open": True, "message": "Open now", "next_opening_time": None}
    return {"is_open": False, "message": "Closed now", "next_opening_time": f"{row.opens_at}"}
