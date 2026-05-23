from app.database import models
from app.services import email_service


def _build_order(db_session):
    settings = models.RestaurantSettings(
        restaurant_name="Pizzeria Pro",
        public_phone="12345",
        whatsapp_number="999",
        delivery_fee=2,
        minimum_order_amount=0,
        estimated_delivery_minutes=30,
        is_accepting_orders=True,
    )
    db_session.add(settings)
    order = models.Order(
        status="accepted",
        customer_name="Ana",
        customer_email="ana@example.com",
        customer_phone="111",
        delivery_address="Main",
        delivery_city="Dublin",
        delivery_postal_code="N37",
        payment_method="card",
        delivery_fee=2,
        total_price=12,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        models.OrderItem(
            order_id=order.id,
            product_id=1,
            product_name="Pizza",
            quantity=1,
            price=10,
            extras="extra queso",
        )
    )
    db_session.commit()
    db_session.refresh(order)
    return order


def test_confirmation_email_generates_html_and_tracking_link(db_session, monkeypatch):
    order = _build_order(db_session)
    captured = {}

    def fake_send_email(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(email_service, "_send_email", fake_send_email)

    sent = email_service.send_order_confirmation_email(db_session, order, payment_method="card")
    assert sent is True
    assert "Pizzeria Pro" in captured["subject"]
    assert "order-tracking?orderId=" in captured["html_body"]
    assert "extra queso" in captured["html_body"]


def test_no_smtp_does_not_break_and_returns_false(db_session, monkeypatch):
    order = _build_order(db_session)
    monkeypatch.setattr(email_service, "SMTP_HOST", "")
    assert (
        email_service.send_order_confirmation_email(db_session, order, payment_method="card")
        is False
    )
