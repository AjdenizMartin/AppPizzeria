import logging

from sqlalchemy.orm import Session

from app.database import models


def _payload(product_id: int):
    return {
        "items": [{"product_id": product_id, "quantity": 1, "extras": ""}],
        "customer_name": "Ana",
        "customer_email": "ana@example.com",
        "customer_phone": "111111",
        "delivery_address": "Main",
        "delivery_city": "Dublin",
        "delivery_postal_code": "N37",
        "delivery_notes": "",
        "payment_method": "card",
    }


def _product(db_session: Session):
    product = models.Product(name="P", price=10, category="Pizzas", description="x")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def test_ready_email_sent_on_transition(
    client, db_session: Session, admin_auth_headers, monkeypatch
):
    product = _product(db_session)
    created = client.post("/orders", json=_payload(product.id)).json()["order_id"]
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "paid"}, headers=admin_auth_headers
    )
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "accepted"}, headers=admin_auth_headers
    )
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "printing"}, headers=admin_auth_headers
    )
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "printed"}, headers=admin_auth_headers
    )

    called = {"count": 0}

    def fake_ready(db, order):
        called["count"] += 1
        return True

    monkeypatch.setattr("app.services.order_service.send_order_ready_email", fake_ready)

    response = client.patch(
        f"/admin/orders/{created}/status",
        json={"status": "ready"},
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    assert called["count"] == 1


def test_ready_transition_survives_email_failure(
    client, db_session: Session, admin_auth_headers, monkeypatch, caplog
):
    product = _product(db_session)
    created = client.post("/orders", json=_payload(product.id)).json()["order_id"]
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "paid"}, headers=admin_auth_headers
    )
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "accepted"}, headers=admin_auth_headers
    )
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "printing"}, headers=admin_auth_headers
    )
    client.patch(
        f"/admin/orders/{created}/status", json={"status": "printed"}, headers=admin_auth_headers
    )

    def broken_ready_email(db, order):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(
        "app.services.order_service.send_order_ready_email",
        broken_ready_email,
    )

    with caplog.at_level(logging.ERROR, logger="app.services.order_service"):
        response = client.patch(
            f"/admin/orders/{created}/status",
            json={"status": "ready"},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert "order_email_failed" in caplog.text


def test_cancelled_email_sent_on_transition(
    client, db_session: Session, admin_auth_headers, monkeypatch
):
    product = _product(db_session)
    created = client.post("/orders", json=_payload(product.id)).json()["order_id"]
    called = {"count": 0}

    def fake_cancel(db, order):
        called["count"] += 1
        return True

    monkeypatch.setattr("app.services.order_service.send_order_cancelled_email", fake_cancel)

    response = client.patch(
        f"/admin/orders/{created}/status",
        json={"status": "cancelled"},
        headers=admin_auth_headers,
    )
    assert response.status_code == 200
    assert called["count"] == 1


def test_cancelled_transition_survives_email_failure(
    client, db_session: Session, admin_auth_headers, monkeypatch, caplog
):
    product = _product(db_session)
    created = client.post("/orders", json=_payload(product.id)).json()["order_id"]

    def broken_cancel_email(db, order):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(
        "app.services.order_service.send_order_cancelled_email",
        broken_cancel_email,
    )

    with caplog.at_level(logging.ERROR, logger="app.services.order_service"):
        response = client.patch(
            f"/admin/orders/{created}/status",
            json={"status": "cancelled"},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert "order_email_failed" in caplog.text


def test_no_duplicate_email_for_same_status(
    client, db_session: Session, admin_auth_headers, monkeypatch
):
    product = _product(db_session)
    created = client.post("/orders", json=_payload(product.id)).json()["order_id"]
    calls = {"count": 0}

    def fake_cancel(db, order):
        calls["count"] += 1
        return True

    monkeypatch.setattr("app.services.order_service.send_order_cancelled_email", fake_cancel)

    first = client.patch(
        f"/admin/orders/{created}/status",
        json={"status": "cancelled"},
        headers=admin_auth_headers,
    )
    assert first.status_code == 200

    second = client.patch(
        f"/admin/orders/{created}/status",
        json={"status": "cancelled"},
        headers=admin_auth_headers,
    )
    assert second.status_code == 200
    assert calls["count"] == 1
