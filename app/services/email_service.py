import logging
import smtplib
from email.message import EmailMessage

from app.core.config import (
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)
from app.database import models

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM_EMAIL)


def _format_order_lines(order: models.Order) -> str:
    if not order.items:
        return "No order items were found."

    lines = []
    for item in order.items:
        extras = f" (extras: {item.extras})" if item.extras else ""
        product_name = (
            item.product_name.strip() if item.product_name else f"Product #{item.product_id}"
        )
        lines.append(
            f"- {product_name} x{item.quantity} · EUR {float(item.price):.2f}{extras}"
        )
    return "\n".join(lines)


def send_order_confirmation_email(order: models.Order, *, payment_method: str) -> bool:
    recipient = (order.customer_email or "").strip().lower()
    if not recipient:
        return False

    if not is_email_configured():
        logger.info(
            "Skipping order confirmation email for order %s: SMTP is not configured",
            order.id,
        )
        return False

    subject = f"Pizzeria order confirmation #{order.id}"
    body = (
        "Thanks for your order.\n\n"
        f"Order ID: {order.id}\n"
        f"Payment method: {payment_method}\n"
        f"Current status: {order.status}\n"
        f"Total: EUR {float(order.total_price):.2f}\n\n"
        "Items:\n"
        f"{_format_order_lines(order)}\n\n"
        "We will notify you again if your order status changes."
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception:
        logger.exception(
            "Failed sending order confirmation email for order %s to %s",
            order.id,
            recipient,
        )
        return False

    logger.info("Order confirmation email sent for order %s to %s", order.id, recipient)
    return True
