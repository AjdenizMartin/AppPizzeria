from sqlalchemy.orm import Session

from app.database import models
from app.schemas.order import OrderCreate
from app.services.printing_service import (
    enqueue_print_job,
    get_order_with_details,
    list_recent_orders,
    request_reprint,
)

ALLOWED_ORDER_TRANSITIONS = {
    "created": {"paid", "cancelled"},
    "pending": {"paid", "cancelled"},
    "paid": {"accepted", "cancelled"},
    "accepted": {"printing", "failed", "cancelled"},
    "printing": {"printed", "failed", "accepted"},
    "printed": {"ready", "delivered"},
    "ready": {"delivered"},
    "failed": {"accepted", "cancelled"},
    "cancelled": set(),
    "delivered": set(),
}


def create_order(db: Session, payload: OrderCreate) -> dict[str, float | int | str]:
    if not payload.items:
        raise ValueError("No items provided")

    order = models.Order(status="created", total_price=0)
    db.add(order)
    db.flush()

    total = 0.0
    created_items = 0

    for item in payload.items:
        product = db.get(models.Product, item.product_id)

        if product is None:
            continue

        total += product.price * item.quantity
        created_items += 1

        db.add(
            models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                price=product.price,
                extras=item.extras,
            )
        )

    if created_items == 0:
        db.rollback()
        raise ValueError("No valid products found")

    order.total_price = total
    db.commit()
    db.refresh(order)

    return {"order_id": order.id, "total": total, "status": order.status}


def create_cash_checkout_order(db: Session, payload: OrderCreate) -> dict[str, float | int | str]:
    order_data = create_order(db, payload)
    order = get_order_with_details(db, int(order_data["order_id"]))

    if order is None:
        raise LookupError("Order not found after creation")

    order.status = "accepted"
    enqueue_print_job(
        db,
        order,
        idempotency_key=f"order-{order.id}-cash-checkout",
    )
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "total": float(order.total_price),
        "status": order.status,
        "payment_method": "cash",
    }


def list_orders(db: Session, *, limit: int = 50) -> list[models.Order]:
    return list_recent_orders(db, limit=limit)


def update_order_status(db: Session, *, order_id: int, next_status: str) -> models.Order:
    order = get_order_with_details(db, order_id)
    if order is None:
        raise LookupError("Order not found")

    current_status = (order.status or "created").lower()
    normalized_next = next_status.lower().strip()

    if current_status == normalized_next:
        return order

    allowed = ALLOWED_ORDER_TRANSITIONS.get(current_status, set())
    if normalized_next not in allowed:
        raise ValueError(
            f"Invalid transition from '{current_status}' to '{normalized_next}'"
        )

    order.status = normalized_next

    if normalized_next == "accepted":
        enqueue_print_job(
            db,
            order,
            idempotency_key=f"order-{order.id}-accepted",
        )

    db.commit()
    refreshed = get_order_with_details(db, order.id)
    if refreshed is None:
        raise LookupError("Order not found after update")
    return refreshed


def requeue_order_print(db: Session, *, order_id: int) -> tuple[models.Order, models.PrintJob]:
    order = get_order_with_details(db, order_id)
    if order is None:
        raise LookupError("Order not found")

    if order.status == "cancelled":
        raise ValueError("Cancelled orders cannot be printed")

    job = request_reprint(db, order)
    db.commit()

    refreshed_order = get_order_with_details(db, order.id)
    if refreshed_order is None:
        raise LookupError("Order not found after reprint request")
    return refreshed_order, job
