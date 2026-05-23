from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_owner
from app.schemas.opening_hours import (
    OpeningHourRead,
    OpeningHourUpdate,
    RestaurantStatusRead,
    TemporaryClosureUpdate,
)
from app.schemas.restaurant import (
    RestaurantSettingsAdminRead,
    RestaurantSettingsPublic,
    RestaurantSettingsUpdate,
)
from app.services.restaurant_service import (
    get_or_create_settings,
    is_restaurant_open,
    list_opening_hours,
    replace_opening_hours,
    update_settings,
)

router = APIRouter(tags=["restaurant"])


@router.get("/restaurant/settings", response_model=RestaurantSettingsPublic)
def get_restaurant_settings(db: Session = Depends(get_db)):
    return get_or_create_settings(db)


@router.get("/restaurant/status", response_model=RestaurantStatusRead)
def get_restaurant_status(db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    status = is_restaurant_open(db)
    return {
        "is_open": status["is_open"],
        "message": status["message"],
        "estimated_delivery_minutes": settings.estimated_delivery_minutes,
        "next_opening_time": status.get("next_opening_time"),
    }


@router.get("/admin/restaurant/settings", response_model=RestaurantSettingsAdminRead)
def get_admin_restaurant_settings(
    db: Session = Depends(get_db),
    _current_admin=Depends(require_owner),
):
    return get_or_create_settings(db)


@router.patch("/admin/restaurant/settings", response_model=RestaurantSettingsAdminRead)
def patch_admin_restaurant_settings(
    payload: RestaurantSettingsUpdate,
    db: Session = Depends(get_db),
    _current_admin=Depends(require_owner),
):
    return update_settings(db, payload=payload.model_dump())


@router.get("/admin/restaurant/opening-hours", response_model=list[OpeningHourRead])
def get_admin_opening_hours(
    db: Session = Depends(get_db),
    _current_admin=Depends(require_owner),
):
    return list_opening_hours(db)


@router.put("/admin/restaurant/opening-hours", response_model=list[OpeningHourRead])
def put_admin_opening_hours(
    payload: list[OpeningHourUpdate],
    db: Session = Depends(get_db),
    _current_admin=Depends(require_owner),
):
    return replace_opening_hours(db, payload=[item.model_dump() for item in payload])


@router.patch("/admin/restaurant/temporary-closure", response_model=RestaurantSettingsAdminRead)
def patch_admin_temporary_closure(
    payload: TemporaryClosureUpdate,
    db: Session = Depends(get_db),
    _current_admin=Depends(require_owner),
):
    return update_settings(
        db,
        payload={
            "temporary_closed": payload.temporary_closed,
            "temporary_closed_message": payload.temporary_closed_message or "",
        },
    )
