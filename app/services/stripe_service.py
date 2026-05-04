import json
import logging
from urllib.parse import urljoin

import stripe

from app.core.config import APP_ENV, FRONTEND_BASE_URL, STRIPE_KEY, STRIPE_WEBHOOK_SECRET
from app.schemas.payment import CheckoutItem

logger = logging.getLogger(__name__)


def _configure_stripe() -> None:
    if not STRIPE_KEY:
        raise ValueError("Stripe API key not found. Check your .env file.")

    if not STRIPE_KEY.startswith("sk_"):
        raise ValueError("Stripe API key must be a secret key starting with 'sk_'.")

    stripe.api_key = STRIPE_KEY


def create_checkout(items: list[CheckoutItem], *, order_id: int | None = None) -> str:
    _configure_stripe()

    if not items:
        raise ValueError("No items provided for checkout")

    line_items = []

    for item in items:
        line_items.append({
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": item.name,
                },
                "unit_amount": int(item.price * 100),
            },
            "quantity": item.quantity,
        })

    cancel_url = urljoin(f"{FRONTEND_BASE_URL}/", "checkout")
    success_url = cancel_url
    if order_id is not None:
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

    if order_id is not None:
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
