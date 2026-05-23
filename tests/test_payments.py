from sqlalchemy.orm import Session

from app.database import models


def _order_payload(product_id: int) -> dict:
    return {
        "items": [{"product_id": product_id, "quantity": 1, "extras": ""}],
        "customer_name": "Angel Client",
        "customer_email": "client@example.com",
        "customer_phone": "0899730419",
        "delivery_address": "Bastion Quay c33",
        "delivery_city": "Athlone",
        "delivery_postal_code": "N37XF78",
        "delivery_notes": "",
        "payment_method": "card",
        "delivery_fee": 2.5,
    }


def test_checkout_returns_url(client, monkeypatch):
    def fake_create_checkout_for_order(db, *, order_id):
        assert order_id == 7
        return "https://example.com/checkout"

    monkeypatch.setattr(
        "app.routers.payments.create_checkout_for_order",
        fake_create_checkout_for_order,
    )

    response = client.post(
        "/create-checkout-session",
        json={"order_id": 7},
    )

    assert response.status_code == 200
    assert response.json() == {"url": "https://example.com/checkout"}


def test_checkout_fails_if_order_not_found(client):
    response = client.post("/create-checkout-session", json={"order_id": 999999})
    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found"}


def test_stripe_webhook_marks_paid_order(client, monkeypatch):
    def fake_construct_event(payload, signature):
        assert signature == "test-signature"
        return {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"order_id": "12"}}},
        }

    called = {}

    def fake_mark_order_paid_after_checkout(db, *, order_id):
        called["order_id"] = order_id

    monkeypatch.setattr("app.routers.payments.construct_webhook_event", fake_construct_event)
    monkeypatch.setattr(
        "app.routers.payments.mark_order_paid_after_checkout",
        fake_mark_order_paid_after_checkout,
    )

    response = client.post(
        "/stripe/webhook",
        data=b'{"type":"checkout.session.completed"}',
        headers={"Stripe-Signature": "test-signature"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert called == {"order_id": 12}


def test_stripe_webhook_marks_accepted_and_enqueues_print_job(
    client, db_session: Session, monkeypatch
):
    product = models.Product(
        name="Webhook Pizza",
        price=14.0,
        category="Pizzas",
        description="Webhook item",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create_order_response = client.post(
        "/orders",
        json=_order_payload(product.id),
    )
    assert create_order_response.status_code == 201
    order_id = create_order_response.json()["order_id"]

    def fake_construct_event(payload, signature):
        assert signature == "test-signature"
        return {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"order_id": str(order_id)}}},
        }

    monkeypatch.setattr("app.routers.payments.construct_webhook_event", fake_construct_event)

    webhook_response = client.post(
        "/stripe/webhook",
        data=b'{"type":"checkout.session.completed"}',
        headers={"Stripe-Signature": "test-signature"},
    )
    assert webhook_response.status_code == 200
    assert webhook_response.json() == {"ok": True}

    db_session.expire_all()
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert order.status == "accepted"
    assert len(order.print_jobs) == 1
    assert order.print_jobs[0].status == "pending"
    assert order.print_jobs[0].idempotency_key == f"order-{order_id}-stripe-paid"


def test_stripe_webhook_rejects_missing_secret_in_production(client, monkeypatch):
    monkeypatch.setattr("app.services.stripe_service.APP_ENV", "production")
    monkeypatch.setattr("app.services.stripe_service.STRIPE_WEBHOOK_SECRET", "")
    monkeypatch.setattr("app.services.stripe_service.STRIPE_KEY", "sk_test_123")

    response = client.post(
        "/stripe/webhook",
        data=b'{"type":"checkout.session.completed"}',
        headers={"Stripe-Signature": "test-signature"},
    )

    assert response.status_code == 503
    assert "STRIPE_WEBHOOK_SECRET" in response.json()["detail"]


def test_non_completed_webhook_does_not_mark_order_paid(client, db_session: Session, monkeypatch):
    product = models.Product(
        name="Webhook Keep Created",
        price=10.0,
        category="Pizzas",
        description="No payment confirmation",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create_order_response = client.post("/orders", json=_order_payload(product.id))
    assert create_order_response.status_code == 201
    order_id = create_order_response.json()["order_id"]

    def fake_construct_event(payload, signature):
        return {"type": "checkout.session.async_payment_failed", "data": {"object": {}}}

    monkeypatch.setattr("app.routers.payments.construct_webhook_event", fake_construct_event)
    response = client.post("/stripe/webhook", data=b"{}")
    assert response.status_code == 200
    assert response.json()["ignored"] is True

    db_session.expire_all()
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert order.status == "created"


def test_create_checkout_uses_db_prices_and_delivery_fee(
    monkeypatch, db_session: Session
):
    from app.services import stripe_service

    monkeypatch.setattr(stripe_service, "STRIPE_KEY", "sk_test_123")
    monkeypatch.setattr(stripe_service, "FRONTEND_BASE_URL", "http://127.0.0.1:5173")

    order = models.Order(
        status="created",
        total_price=22.5,
        customer_name="Client",
        customer_email="client@example.com",
        customer_phone="0899730419",
        delivery_address="Addr",
        delivery_city="City",
        delivery_postal_code="X1",
        payment_method="card",
        delivery_fee=2.5,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        models.OrderItem(
            order_id=order.id,
            product_id=1,
            product_name="Pizza",
            quantity=2,
            price=10.0,
            extras="",
        )
    )
    db_session.commit()

    captured = {}

    class FakeSession:
        url = "https://stripe.test/session"

    def fake_create(**payload):
        captured["payload"] = payload
        return FakeSession()

    monkeypatch.setattr("stripe.checkout.Session.create", fake_create)

    url = stripe_service.create_checkout_for_order(db_session, order_id=order.id)

    assert url == "https://stripe.test/session"
    assert len(captured["payload"]["line_items"]) == 2
    assert captured["payload"]["line_items"][0]["price_data"]["unit_amount"] == 1000
    assert captured["payload"]["line_items"][0]["quantity"] == 2
    assert (
        captured["payload"]["line_items"][1]["price_data"]["product_data"]["name"]
        == "Delivery fee"
    )
    assert captured["payload"]["line_items"][1]["price_data"]["unit_amount"] == 250
    assert (
        captured["payload"]["success_url"]
        == f"http://127.0.0.1:5173/order-confirmation/{order.id}?method=card"
    )
    assert captured["payload"]["cancel_url"] == "http://127.0.0.1:5173/checkout"
    assert captured["payload"]["metadata"]["order_id"] == str(order.id)


def test_checkout_ignores_frontend_prices_payload(client, monkeypatch):
    captured = {}

    def fake_create_checkout_for_order(db, *, order_id):
        captured["order_id"] = order_id
        return "https://example.com/checkout"

    monkeypatch.setattr(
        "app.routers.payments.create_checkout_for_order",
        fake_create_checkout_for_order,
    )
    response = client.post(
        "/create-checkout-session",
        json={
            "order_id": 15,
            "items": [{"name": "Injected", "price": 0.01, "quantity": 99}],
        },
    )
    assert response.status_code == 200
    assert captured["order_id"] == 15


def test_checkout_fails_if_order_total_is_zero(db_session: Session):
    from app.services import stripe_service

    stripe_service.STRIPE_KEY = "sk_test_123"

    order = models.Order(
        status="created",
        total_price=0,
        customer_name="Client",
        customer_email="client@example.com",
        customer_phone="0899730419",
        delivery_address="Addr",
        delivery_city="City",
        delivery_postal_code="X1",
        payment_method="card",
        delivery_fee=0,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        models.OrderItem(
            order_id=order.id,
            product_id=1,
            product_name="Pizza",
            quantity=1,
            price=0,
            extras="",
        )
    )
    db_session.commit()

    try:
        stripe_service.create_checkout_for_order(db_session, order_id=order.id)
    except ValueError as exc:
        assert "total" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for zero total")


def test_checkout_fails_if_order_is_cancelled(db_session: Session):
    from app.services import stripe_service

    stripe_service.STRIPE_KEY = "sk_test_123"
    order = models.Order(
        status="cancelled",
        total_price=12.5,
        customer_name="Client",
        customer_email="client@example.com",
        customer_phone="0899730419",
        delivery_address="Addr",
        delivery_city="City",
        delivery_postal_code="X1",
        payment_method="card",
        delivery_fee=2.5,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        models.OrderItem(
            order_id=order.id,
            product_id=1,
            product_name="Pizza",
            quantity=1,
            price=10.0,
            extras="",
        )
    )
    db_session.commit()

    try:
        stripe_service.create_checkout_for_order(db_session, order_id=order.id)
    except ValueError as exc:
        assert "cancelled" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for cancelled order")
