from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import models
from app.schemas.order import OrderCreate
from app.services.email_service import (
    send_order_cancelled_email,
    send_order_confirmation_email,
    send_order_ready_email,
)
from app.services.order_status_event_service import add_status_event
from app.services.printing_service import (
    enqueue_print_job,
    get_order_with_details,
    list_recent_orders,
    request_reprint,
)
from app.services.restaurant_service import get_or_create_settings, is_restaurant_open

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


def create_order(
    db: Session,
    payload: OrderCreate,
    *,
    current_user: models.User | None = None,
) -> dict[str, Decimal | int | str]:
    if not payload.items:
        raise ValueError("No items provided")

    customer_name = payload.customer_name.strip()
    customer_email = payload.customer_email.strip().lower()
    customer_phone = payload.customer_phone.strip()
    delivery_address = payload.delivery_address.strip()
    delivery_city = payload.delivery_city.strip()
    delivery_postal_code = payload.delivery_postal_code.strip()
    delivery_notes = payload.delivery_notes.strip()

    if not customer_name or not customer_email or not customer_phone:
        raise ValueError("Customer name, email and phone are required")
    if not delivery_address or not delivery_city or not delivery_postal_code:
        raise ValueError("Delivery address, city and postal code are required")

    try:
        settings = get_or_create_settings(db)
        open_status = is_restaurant_open(db)
        if not open_status["is_open"]:
            raise ValueError(open_status["message"])
        if not settings.is_accepting_orders:
            raise ValueError("Orders are currently paused by the restaurant")
        order = models.Order(
            status="created",
            total_price=Decimal("0"),
            user_id=current_user.id if current_user else None,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            delivery_city=delivery_city,
            delivery_postal_code=delivery_postal_code,
            delivery_notes=delivery_notes or None,
            payment_method=payload.payment_method,
            delivery_fee=Decimal(str(settings.delivery_fee)),
        )
        db.add(order)
        db.flush()

        total = Decimal("0")
        created_items = 0

        for item in payload.items:
            product = db.get(models.Product, item.product_id)

            if product is None:
                continue
            if not product.is_available:
                raise ValueError(f"Product '{product.name}' is sold out")

            total += Decimal(str(product.price)) * item.quantity
            created_items += 1

            db.add(
                models.OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=item.quantity,
                    price=product.price,
                    extras=item.extras,
                )
            )

        if created_items == 0:
            raise ValueError("No valid products found")

        if total < Decimal(str(settings.minimum_order_amount)):
            raise ValueError(
                f"Minimum order amount is EUR {float(settings.minimum_order_amount):.2f}"
            )

        order.total_price = total + Decimal(str(settings.delivery_fee))
        add_status_event(
            db,
            order=order,
            old_status=None,
            new_status="created",
            source="customer",
            changed_by_user_id=current_user.id if current_user else None,
        )
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise

    return {"order_id": order.id, "total": order.total_price, "status": order.status}


def create_cash_checkout_order(
    db: Session,
    payload: OrderCreate,
    *,
    current_user: models.User | None = None,
) -> dict[str, float | int | str]:
    cash_payload = payload.model_copy(update={"payment_method": "cash"})
    order_data = create_order(db, cash_payload, current_user=current_user)
    try:
        order = get_order_with_details(db, int(order_data["order_id"]))

        if order is None:
            raise LookupError("Order not found after creation")

        order.status = "accepted"
        add_status_event(
            db,
            order=order,
            old_status="created",
            new_status="accepted",
            source="system",
            changed_by_user_id=current_user.id if current_user else None,
            note="cash checkout",
        )
        enqueue_print_job(
            db,
            order,
            idempotency_key=f"order-{order.id}-cash-checkout",
        )
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        raise
    send_order_confirmation_email(db, order, payment_method="cash")

    return {
        "order_id": order.id,
        "total": float(order.total_price),
        "status": order.status,
        "payment_method": "cash",
    }


def mark_order_paid_after_checkout(db: Session, *, order_id: int) -> models.Order:
    order = get_order_with_details(db, order_id)
    if order is None:
        raise LookupError("Order not found")

    current_status = (order.status or "created").lower()
    if current_status in {"printing", "printed", "ready", "delivered"}:
        return order

    if current_status == "cancelled":
        raise ValueError("Cannot mark a cancelled order as paid")

    order.status = "accepted"
    order.payment_method = "card"
    add_status_event(
        db,
        order=order,
        old_status=current_status,
        new_status="accepted",
        source="stripe",
    )
    enqueue_print_job(
        db,
        order,
        idempotency_key=f"order-{order.id}-stripe-paid",
    )
    db.commit()
    db.refresh(order)
    send_order_confirmation_email(db, order, payment_method="card")
    return order


def list_orders(
    db: Session,
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    payment_method: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.Order]:
    return list_recent_orders(
        db,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        payment_method=payment_method,
        limit=limit,
        offset=offset,
    )


def get_order_for_tracking(
    db: Session,
    *,
    order_id: int,
    email: str | None = None,
    phone: str | None = None,
) -> models.Order:
    order = get_order_with_details(db, order_id)
    if order is None:
        raise LookupError("Order not found")

    normalized_email = (email or "").strip().lower()
    normalized_phone = (phone or "").strip()
    if not normalized_email and not normalized_phone:
        raise ValueError("Email or phone is required")

    email_match = bool(
        normalized_email and (order.customer_email or "").lower() == normalized_email
    )
    phone_match = bool(normalized_phone and (order.customer_phone or "") == normalized_phone)
    if not email_match and not phone_match:
        raise PermissionError("Order not found")

    return order


def update_order_status(
    db: Session,
    *,
    order_id: int,
    next_status: str,
    changed_by_user_id: int | None = None,
) -> models.Order:
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

    try:
        order.status = normalized_next
        add_status_event(
            db,
            order=order,
            old_status=current_status,
            new_status=normalized_next,
            source="admin",
            changed_by_user_id=changed_by_user_id,
        )

        if normalized_next == "accepted":
            enqueue_print_job(
                db,
                order,
                idempotency_key=f"order-{order.id}-accepted",
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    refreshed = get_order_with_details(db, order.id)
    if refreshed is None:
        raise LookupError("Order not found after update")
    if normalized_next == "ready":
        send_order_ready_email(db, refreshed)
    elif normalized_next == "cancelled":
        send_order_cancelled_email(db, refreshed)
    return refreshed


def requeue_order_print(
    db: Session,
    *,
    order_id: int,
    changed_by_user_id: int | None = None,
) -> tuple[models.Order, models.PrintJob]:
    order = get_order_with_details(db, order_id)
    if order is None:
        raise LookupError("Order not found")

    if order.status == "cancelled":
        raise ValueError("Cancelled orders cannot be printed")

    try:
        previous_status = order.status
        job = request_reprint(db, order)
        add_status_event(
            db,
            order=order,
            old_status=previous_status,
            new_status=order.status,
            source="admin",
            changed_by_user_id=changed_by_user_id,
            note=f"reprint requested job:{job.id}",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    refreshed_order = get_order_with_details(db, order.id)
    if refreshed_order is None:
        raise LookupError("Order not found after reprint request")
    return refreshed_order, job
