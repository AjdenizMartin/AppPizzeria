import stripe

from app.core.config import FRONTEND_BASE_URL, STRIPE_KEY
from app.schemas.payment import CheckoutItem


def _configure_stripe() -> None:
    if not STRIPE_KEY:
        raise ValueError("Stripe API key not found. Check your .env file.")

    if not STRIPE_KEY.startswith("sk_"):
        raise ValueError("Stripe API key must be a secret key starting with 'sk_'.")

    stripe.api_key = STRIPE_KEY


def create_checkout(items: list[CheckoutItem]) -> str:
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

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=f"{FRONTEND_BASE_URL}/success.html",
        cancel_url=FRONTEND_BASE_URL,
    )

    return session.url
