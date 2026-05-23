from sqlalchemy.orm import Session

from app.database import models


def _payload(product_id: int, payment_method: str = "card") -> dict:
    return {
        "items": [{"product_id": product_id, "quantity": 1, "extras": ""}],
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "customer_phone": "111111",
        "delivery_address": "Main",
        "delivery_city": "Dublin",
        "delivery_postal_code": "N37",
        "delivery_notes": "",
        "payment_method": payment_method,
    }


def _create_product(db_session: Session) -> models.Product:
    product = models.Product(name="P", price=10, category="Pizzas", description="x")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def test_create_order_registers_created_event(client, db_session: Session):
    product = _create_product(db_session)
    response = client.post("/orders", json=_payload(product.id))
    assert response.status_code == 201
    order_id = response.json()["order_id"]
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert order.status_events
    assert order.status_events[0].new_status == "created"


def test_cash_checkout_registers_accepted_event(client, db_session: Session):
    product = _create_product(db_session)
    response = client.post(
        "/orders/cash-checkout",
        json=_payload(product.id, payment_method="cash"),
    )
    assert response.status_code == 201
    order = db_session.get(models.Order, response.json()["order_id"])
    assert order is not None
    assert any(evt.new_status == "accepted" for evt in order.status_events)


def test_admin_status_change_registers_old_new(client, db_session: Session, admin_auth_headers):
    product = _create_product(db_session)
    created = client.post("/orders", json=_payload(product.id))
    order_id = created.json()["order_id"]
    updated = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "paid"},
        headers=admin_auth_headers,
    )
    assert updated.status_code == 200
    order = db_session.get(models.Order, order_id)
    paid_event = [evt for evt in order.status_events if evt.new_status == "paid"][-1]
    assert paid_event.old_status == "created"


def test_tracking_does_not_expose_internal_fields(client, db_session: Session):
    product = _create_product(db_session)
    created = client.post("/orders", json=_payload(product.id))
    order_id = created.json()["order_id"]
    tracking = client.get(f"/orders/{order_id}/tracking?email=ana@example.com")
    assert tracking.status_code == 200
    assert tracking.json()["status_events"]
    first = tracking.json()["status_events"][0]
    assert "changed_by_user_id" not in first
    assert "source" not in first


def test_admin_response_contains_status_events(client, db_session: Session, admin_auth_headers):
    product = _create_product(db_session)
    client.post("/orders", json=_payload(product.id))
    response = client.get("/admin/orders", headers=admin_auth_headers)
    assert response.status_code == 200
    assert "status_events" in response.json()[0]
