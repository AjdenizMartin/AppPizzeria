from sqlalchemy.orm import Session

from app.database import models


def add_status_event(
    db: Session,
    *,
    order: models.Order,
    new_status: str,
    old_status: str | None = None,
    source: str,
    changed_by_user_id: int | None = None,
    note: str | None = None,
) -> None:
    normalized_new = new_status.strip().lower()
    normalized_old = old_status.strip().lower() if old_status else None

    if normalized_old == normalized_new:
        return

    existing_latest = (
        db.query(models.OrderStatusEvent)
        .filter(models.OrderStatusEvent.order_id == order.id)
        .order_by(models.OrderStatusEvent.id.desc())
        .first()
    )
    if (
        existing_latest
        and existing_latest.new_status == normalized_new
        and existing_latest.source == source
        and existing_latest.note == note
    ):
        return

    db.add(
        models.OrderStatusEvent(
            order_id=order.id,
            old_status=normalized_old,
            new_status=normalized_new,
            changed_by_user_id=changed_by_user_id,
            source=source,
            note=note,
        )
    )
