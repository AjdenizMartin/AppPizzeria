from datetime import UTC, datetime

from app.database import models


def _register_admin(client):
    response = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _order_payload(product_id: int, *, postal_code: str = "D01A123", quantity: int = 1):
    return {
        "items": [{"product_id": product_id, "quantity": quantity, "extras": "sin cebolla"}],
        "customer_name": "Ana Client",
        "customer_email": "ana@example.com",
        "customer_phone": "0899730419",
        "delivery_address": "Bastion Quay c33",
        "delivery_city": "Athlone",
        "delivery_postal_code": postal_code,
        "delivery_notes": "Call on arrival",
        "payment_method": "card",
    }


def test_full_real_flow_card_checkout_to_delivered_and_reports(client, db_session, monkeypatch):
    admin_headers = _register_admin(client)

    product = models.Product(
        name="Margherita",
        price=10.0,
        category="Pizzas",
        description="Classic",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    client.patch(
        "/admin/restaurant/settings",
        json={
            "restaurant_name": "Pizzeria Pro",
            "is_accepting_orders": True,
            "minimum_order_amount": 0,
            "estimated_delivery_minutes": 30,
        },
        headers=admin_headers,
    )
    client.put(
        "/admin/restaurant/opening-hours",
        json=[
            {"day_of_week": d, "opens_at": "00:00", "closes_at": "23:59", "is_closed": False}
            for d in range(7)
        ],
        headers=admin_headers,
    )

    created = client.post("/orders", json=_order_payload(product.id))
    assert created.status_code == 201
    order_id = created.json()["order_id"]

    def fake_checkout_create(**kwargs):
        class FakeSession:
            url = "https://stripe.test/checkout"

        return FakeSession()

    monkeypatch.setattr("stripe.checkout.Session.create", fake_checkout_create)
    checkout = client.post("/create-checkout-session", json={"order_id": order_id})
    assert checkout.status_code == 200
    assert checkout.json()["url"] == "https://stripe.test/checkout"

    def fake_construct_event(payload, signature):
        return {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"order_id": str(order_id)}}},
        }

    monkeypatch.setattr("app.routers.payments.construct_webhook_event", fake_construct_event)
    webhook = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "test-signature"},
    )
    assert webhook.status_code == 200

    db_session.expire_all()
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert order.status == "accepted"
    assert len(order.print_jobs) == 1
    assert order.print_jobs[0].status == "pending"

    ok_tracking = client.get(f"/orders/{order_id}/tracking?email=ana@example.com")
    assert ok_tracking.status_code == 200
    assert ok_tracking.json()["status"] == "accepted"
    ok_tracking_phone = client.get(f"/orders/{order_id}/tracking?phone=0899730419")
    assert ok_tracking_phone.status_code == 200
    denied_tracking = client.get(f"/orders/{order_id}/tracking?email=wrong@example.com")
    assert denied_tracking.status_code == 404

    to_printing = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "printing"},
        headers=admin_headers,
    )
    assert to_printing.status_code == 200
    to_printed = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "printed"},
        headers=admin_headers,
    )
    assert to_printed.status_code == 200
    to_ready = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "ready"},
        headers=admin_headers,
    )
    assert to_ready.status_code == 200
    tracking_ready = client.get(f"/orders/{order_id}/tracking?email=ana@example.com")
    assert tracking_ready.status_code == 200
    assert tracking_ready.json()["status"] == "ready"

    report = client.get(
        f"/admin/reports/sales?date={datetime.now(UTC).date().isoformat()}",
        headers=admin_headers,
    )
    assert report.status_code == 200
    assert report.json()["revenue_total"] >= 12.5

    delivered = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=admin_headers,
    )
    assert delivered.status_code == 200

    report_after = client.get(
        f"/admin/reports/sales?date={datetime.now(UTC).date().isoformat()}",
        headers=admin_headers,
    )
    assert report_after.status_code == 200
    assert report_after.json()["revenue_total"] >= report.json()["revenue_total"]


def test_negative_cases_and_duplicate_webhook_idempotency(client, db_session, monkeypatch):
    admin_headers = _register_admin(client)

    client.patch(
        "/admin/restaurant/temporary-closure",
        json={"temporary_closed": False, "temporary_closed_message": ""},
        headers=admin_headers,
    )
    client.put(
        "/admin/restaurant/opening-hours",
        json=[
            {"day_of_week": d, "opens_at": "00:00", "closes_at": "23:59", "is_closed": False}
            for d in range(7)
        ],
        headers=admin_headers,
    )
    client.patch(
        "/admin/restaurant/settings",
        json={
            "restaurant_name": "Pizzeria Pro",
            "public_phone": "12345",
            "whatsapp_number": "999",
            "address": "Main Street",
            "delivery_fee": 2.5,
            "minimum_order_amount": 20,
            "estimated_delivery_minutes": 30,
            "is_accepting_orders": True,
            "banner_text": "",
            "temporary_closed": False,
            "temporary_closed_message": "",
        },
        headers=admin_headers,
    )

    sold_out = models.Product(
        name="Sold Out",
        price=12,
        category="Pizzas",
        description="x",
        is_available=False,
    )
    cheap = models.Product(name="Cheap", price=5, category="Pizzas", description="x")
    db_session.add_all([sold_out, cheap])
    db_session.commit()
    db_session.refresh(sold_out)
    db_session.refresh(cheap)

    sold_out_resp = client.post("/orders", json=_order_payload(sold_out.id))
    assert sold_out_resp.status_code == 400

    low_min_resp = client.post("/orders", json=_order_payload(cheap.id, quantity=1))
    assert low_min_resp.status_code == 400
    assert "minimum" in low_min_resp.json()["detail"].lower()

    client.patch(
        "/admin/restaurant/temporary-closure",
        json={"temporary_closed": True, "temporary_closed_message": "Closed"},
        headers=admin_headers,
    )
    closed_resp = client.post("/orders", json=_order_payload(cheap.id, quantity=5))
    assert closed_resp.status_code == 400

    client.patch(
        "/admin/restaurant/temporary-closure",
        json={"temporary_closed": False, "temporary_closed_message": ""},
        headers=admin_headers,
    )
    valid = client.post("/orders", json=_order_payload(cheap.id, quantity=5))
    assert valid.status_code == 201
    order_id = valid.json()["order_id"]

    def fake_construct_event(payload, signature):
        return {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"order_id": str(order_id)}}},
        }

    monkeypatch.setattr("app.routers.payments.construct_webhook_event", fake_construct_event)
    first = client.post("/stripe/webhook", data=b"{}", headers={"Stripe-Signature": "sig"})
    second = client.post("/stripe/webhook", data=b"{}", headers={"Stripe-Signature": "sig"})
    assert first.status_code == 200
    assert second.status_code == 200

    db_session.expire_all()
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert len(order.print_jobs) == 1
    stripe_events = [
        evt
        for evt in order.status_events
        if evt.new_status == "accepted" and evt.source == "stripe"
    ]
    assert len(stripe_events) == 1
