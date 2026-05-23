# ruff: noqa: E501
import html
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import (
    FRONTEND_BASE_URL,
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)
from app.database import models
from app.services.restaurant_service import get_or_create_settings

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM_EMAIL)


def _format_order_lines_text(order: models.Order) -> str:
    if not order.items:
        return "No order items were found."

    lines = []
    for item in order.items:
        extras = f" (extras: {item.extras})" if item.extras else ""
        product_name = (
            item.product_name.strip() if item.product_name else f"Product #{item.product_id}"
        )
        lines.append(f"- {product_name} x{item.quantity} · EUR {float(item.price):.2f}{extras}")
    return "\n".join(lines)


def _format_order_lines_html(order: models.Order) -> str:
    rows: list[str] = []
    for item in order.items:
        name = html.escape(item.product_name or f"Product #{item.product_id}")
        extras = (
            f"<div style='color:#666;font-size:12px'>Extras: {html.escape(item.extras)}</div>"
            if item.extras
            else ""
        )
        rows.append(
            f"<tr><td style='padding:6px 0'>{name} x{item.quantity}{extras}</td>"
            "<td style='padding:6px 0;text-align:right'>"
            f"EUR {float(item.price) * item.quantity:.2f}</td></tr>"
        )
    return "".join(rows)


def _tracking_link(order: models.Order) -> str:
    email = (order.customer_email or "").strip()
    return (
        f"{FRONTEND_BASE_URL}/order-tracking?orderId={order.id}&email={email}"
        if email
        else f"{FRONTEND_BASE_URL}/order-tracking?orderId={order.id}"
    )


def _send_email(*, recipient: str, subject: str, text_body: str, html_body: str) -> bool:
    if not is_email_configured():
        logger.warning("SMTP not configured. Skipping email to %s", recipient)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            if SMTP_USE_TLS:
                smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception:
        logger.exception("Failed sending email to %s", recipient)
        return False

    return True


def _email_shell(*, business_name: str, title: str, subtitle: str, body_html: str) -> str:
    return f"""
    <html>
      <body style="margin:0;padding:0;background:#f7f7f7;font-family:Arial,sans-serif;color:#1f2937;">  # noqa: E501
        <table role="presentation" style="width:100%;border-collapse:collapse;padding:24px 0;">
          <tr>
            <td align="center">
              <table role="presentation" style="width:100%;max-width:640px;border-collapse:collapse;background:#ffffff;border-radius:14px;overflow:hidden;">  # noqa: E501
                <tr>
                  <td style="padding:24px;background:linear-gradient(135deg,#ff8a00,#e55a08);color:#fff;">  # noqa: E501
                    <div style="font-size:12px;letter-spacing:1.5px;text-transform:uppercase;opacity:.9;">{html.escape(business_name)}</div>  # noqa: E501
                    <div style="font-size:24px;font-weight:700;margin-top:8px;">{html.escape(title)}</div>  # noqa: E501
                    <div style="font-size:14px;margin-top:6px;opacity:.95;">{html.escape(subtitle)}</div>  # noqa: E501
                  </td>
                </tr>
                <tr>
                  <td style="padding:24px;">
                    {body_html}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def send_order_confirmation_email(db, order: models.Order, *, payment_method: str) -> bool:
    recipient = (order.customer_email or "").strip().lower()
    if not recipient:
        return False

    settings = get_or_create_settings(db)
    business_name = settings.restaurant_name or "Pizzeria"
    tracking_link = _tracking_link(order)
    phone = settings.public_phone or ""
    whatsapp = settings.whatsapp_number or ""

    text_body = (
        f"{business_name} - Order confirmation\n\n"
        f"Order ID: {order.id}\n"
        f"Status: {order.status}\n"
        f"Payment method: {payment_method}\n"
        f"Delivery: {order.delivery_address}, {order.delivery_city} {order.delivery_postal_code}\n"
        f"Delivery fee: EUR {float(order.delivery_fee):.2f}\n"
        f"Total: EUR {float(order.total_price):.2f}\n\n"
        f"Items:\n{_format_order_lines_text(order)}\n\n"
        f"Tracking: {tracking_link}\n"
        f"Phone: {phone}\n"
        f"WhatsApp: {whatsapp}\n"
    )

    contact_text = f"Contact: {html.escape(phone)}"
    if whatsapp:
        contact_text += f" · WhatsApp: {html.escape(whatsapp)}"

    delivery_line = (
        f"{html.escape(order.delivery_address)}, "
        f"{html.escape(order.delivery_city)} "
        f"{html.escape(order.delivery_postal_code)}"
    )
    html_body = _email_shell(
        business_name=business_name,
        title="Order confirmed",
        subtitle=f"Order #{order.id}",
        body_html=f"""
          <p style="margin:0 0 12px;"><strong>Status:</strong> {html.escape(order.status)}<br/>
          <strong>Payment:</strong> {html.escape(payment_method)}</p>
          <p style="margin:0 0 16px;"><strong>Delivery:</strong> {delivery_line}</p>
          <table role="presentation" style="width:100%;border-collapse:collapse;font-size:14px;">
            {_format_order_lines_html(order)}
            <tr><td style="padding-top:10px;"><strong>Delivery fee</strong></td><td style="padding-top:10px;text-align:right;"><strong>EUR {float(order.delivery_fee):.2f}</strong></td></tr>  # noqa: E501
            <tr><td style="padding-top:8px;border-top:1px solid #eee;"><strong>Total</strong></td><td style="padding-top:8px;border-top:1px solid #eee;text-align:right;"><strong>EUR {float(order.total_price):.2f}</strong></td></tr>  # noqa: E501
          </table>
          <p style="margin:16px 0 8px;"><a href="{html.escape(tracking_link)}" style="display:inline-block;background:#e55a08;color:#fff;padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:700;">Track your order</a></p>  # noqa: E501
          <p style="margin:8px 0 0;color:#4b5563;font-size:13px;">{contact_text}</p>
        """,
    )

    return _send_email(
        recipient=recipient,
        subject=f"{business_name} order confirmation #{order.id}",
        text_body=text_body,
        html_body=html_body,
    )


def send_order_ready_email(db, order: models.Order) -> bool:
    recipient = (order.customer_email or "").strip().lower()
    if not recipient:
        return False
    settings = get_or_create_settings(db)
    business_name = settings.restaurant_name or "Pizzeria"
    contact = settings.public_phone or settings.whatsapp_number or ""

    text_body = (
        f"{business_name}\n\n"
        f"Your order #{order.id} is ready.\n"
        f"Payment method: {order.payment_method}\n"
        f"Contact: {contact}\n"
    )
    html_body = _email_shell(
        business_name=business_name,
        title="Your order is ready",
        subtitle=f"Order #{order.id}",
        body_html=(
            f"<p style='margin:0 0 12px;'>Your order <strong>#{order.id}</strong> is now "
            "<strong>ready</strong>.</p>"
            f"<p style='margin:0 0 8px;'><strong>Payment:</strong> {html.escape(order.payment_method)}</p>"  # noqa: E501
            f"<p style='margin:0;color:#4b5563;'><strong>Contact:</strong> {html.escape(contact)}</p>"  # noqa: E501
        ),
    )
    return _send_email(
        recipient=recipient,
        subject=f"{business_name} order #{order.id} is ready",
        text_body=text_body,
        html_body=html_body,
    )


def send_order_cancelled_email(db, order: models.Order) -> bool:
    recipient = (order.customer_email or "").strip().lower()
    if not recipient:
        return False
    settings = get_or_create_settings(db)
    business_name = settings.restaurant_name or "Pizzeria"
    card_note = (
        "If you paid by card, the restaurant will review your refund manually."
        if (order.payment_method or "").lower() == "card"
        else ""
    )

    text_body = (
        f"{business_name}\n\n"
        f"Your order #{order.id} has been cancelled.\n"
        "If you have questions, contact the restaurant.\n"
        f"{card_note}\n"
    )
    html_body = _email_shell(
        business_name=business_name,
        title="Order cancelled",
        subtitle=f"Order #{order.id}",
        body_html=(
            f"<p style='margin:0 0 12px;'>Your order <strong>#{order.id}</strong> has been "
            "<strong>cancelled</strong>.</p>"
            "<p style='margin:0 0 8px;'>If you have questions, contact the restaurant.</p>"
            f"<p style='margin:0;color:#4b5563;'>{html.escape(card_note)}</p>"
        ),
    )
    return _send_email(
        recipient=recipient,
        subject=f"{business_name} order #{order.id} cancelled",
        text_body=text_body,
        html_body=html_body,
    )
