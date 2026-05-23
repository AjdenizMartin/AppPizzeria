import json
import logging
from urllib.parse import urljoin

import stripe
from sqlalchemy.orm import Session

from app.core.config import APP_ENV, FRONTEND_BASE_URL, STRIPE_KEY, STRIPE_WEBHOOK_SECRET
from app.services.printing_service import get_order_with_details

logger = logging.getLogger(__name__)


def _configure_stripe() -> None:
    if not STRIPE_KEY:
        raise ValueError("Stripe API key not found. Check your .env file.")

    if not STRIPE_KEY.startswith("sk_"):
        raise ValueError("Stripe API key must be a secret key starting with 'sk_'.")

    stripe.api_key = STRIPE_KEY


def create_checkout_for_order(db: Session, *, order_id: int) -> str:
    _configure_stripe()

    order = get_order_with_details(db, order_id)
    if order is None:
        raise LookupError("Order not found")
    if not order.items:
        raise ValueError("Order has no items")

    status = (order.status or "created").lower()
    if status == "cancelled":
        raise ValueError("Cancelled orders cannot start card checkout")
    if status in {"paid", "accepted", "printing", "printed", "ready", "delivered"}:
        raise ValueError(f"Order is already in status '{status}'")
    if float(order.total_price or 0) <= 0:
        raise ValueError("Order total must be greater than 0")

    line_items = []

    for item in order.items:
        unit_amount = int(float(item.price) * 100)
        if unit_amount <= 0:
            raise ValueError("Order item price must be greater than 0")
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": item.product_name,
                },
                "unit_amount": unit_amount,
            },
            "quantity": item.quantity,
        })

    delivery_fee = float(order.delivery_fee or 0)
    if delivery_fee > 0:
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {"name": "Delivery fee"},
                "unit_amount": int(delivery_fee * 100),
            },
            "quantity": 1,
        })

    cancel_url = urljoin(f"{FRONTEND_BASE_URL}/", "checkout")
    success_url = urljoin(
        f"{FRONTEND_BASE_URL}/",
        f"order-confirmation/{order_id}?method=card",
    )

    session_payload: dict = {
        "payment_method_types": ["card"],
        "line_items": line_items,
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    session_payload["metadata"] = {"order_id": str(order_id)}

    session = stripe.checkout.Session.create(**session_payload)

    return session.url


def construct_webhook_event(payload: bytes, signature: str | None) -> dict:
    _configure_stripe()

    if APP_ENV == "production" and not STRIPE_WEBHOOK_SECRET:
        logger.critical(
            "Stripe webhook rejected in production: STRIPE_WEBHOOK_SECRET is missing"
        )
        raise ValueError("Insecure configuration: STRIPE_WEBHOOK_SECRET is required in production")

    if STRIPE_WEBHOOK_SECRET:
        if not signature:
            raise ValueError("Missing Stripe-Signature header")
        return stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)

    event = stripe.Event.construct_from(json.loads(payload.decode("utf-8")), stripe.api_key)
    return dict(event)
