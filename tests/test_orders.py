import logging

from sqlalchemy.orm import Session

from app.database import models


def _order_payload(product_id: int, quantity: int = 1) -> dict:
    return {
        "items": [{"product_id": product_id, "quantity": quantity, "extras": ""}],
        "customer_name": "Angel Client",
        "customer_email": "client@example.com",
        "customer_phone": "0899730419",
        "delivery_address": "Bastion Quay c33",
        "delivery_city": "Athlone",
        "delivery_postal_code": "N37XF78",
        "delivery_notes": "Call on arrival",
        "payment_method": "card",
        "delivery_fee": 2.5,
    }


def test_create_order_calculates_total(client, db_session: Session):
    product = models.Product(
        name="Burger Meal",
        price=9.5,
        category="Burger Meals",
        description="Combo",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post(
        "/orders",
        json={
            **_order_payload(product.id, quantity=2),
            "items": [{"product_id": product.id, "quantity": 2, "extras": "Extra cheese"}],
        },
    )

    assert response.status_code == 201
    assert response.json() == {"order_id": 1, "total": 21.5, "status": "created"}
    order = db_session.get(models.Order, 1)
    assert order is not None
    assert len(order.items) == 1
    assert order.items[0].extras == "Extra cheese"


def test_create_order_rejects_empty_items(client):
    response = client.post(
        "/orders",
        json={
            "items": [],
            "customer_name": "Angel Client",
            "customer_email": "client@example.com",
            "customer_phone": "0899730419",
            "delivery_address": "Bastion Quay c33",
            "delivery_city": "Athlone",
            "delivery_postal_code": "N37XF78",
            "delivery_notes": "",
            "payment_method": "card",
            "delivery_fee": 2.5,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "No items provided"}


def test_admin_can_progress_order_and_enqueue_print_job(
    client, db_session: Session, admin_auth_headers
):
    product = models.Product(
        name="Pepperoni",
        price=10.0,
        category="Pizzas",
        description="Classic",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create_response = client.post(
        "/orders",
        json=_order_payload(product.id),
    )
    order_id = create_response.json()["order_id"]

    paid_response = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "paid"},
        headers=admin_auth_headers,
    )
    assert paid_response.status_code == 200
    assert paid_response.json()["status"] == "paid"
    assert paid_response.json()["print_jobs"] == []

    accepted_response = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=admin_auth_headers,
    )
    assert accepted_response.status_code == 200
    payload = accepted_response.json()
    assert payload["status"] == "accepted"
    assert len(payload["print_jobs"]) == 1
    assert payload["print_jobs"][0]["status"] == "pending"


def test_admin_rejects_invalid_order_transition(client, db_session: Session, admin_auth_headers):
    product = models.Product(
        name="Cheeseburger",
        price=8.0,
        category="Burgers",
        description="Double patty",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create_response = client.post(
        "/orders",
        json=_order_payload(product.id),
    )
    order_id = create_response.json()["order_id"]

    response = client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "delivered"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 400
    assert "Invalid transition" in response.json()["detail"]


def test_cash_checkout_creates_accepted_order_and_print_job(
    client, db_session: Session, admin_auth_headers
):
    product = models.Product(
        name="Cash Pizza",
        price=11.0,
        category="Pizzas",
        description="Cash order item",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post(
        "/orders/cash-checkout",
        json={**_order_payload(product.id, quantity=2), "payment_method": "cash"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["total"] == 24.5
    assert payload["status"] == "accepted"
    assert payload["payment_method"] == "cash"

    admin_orders_response = client.get("/admin/orders", headers=admin_auth_headers)
    assert admin_orders_response.status_code == 200
    latest_order = admin_orders_response.json()[0]
    assert latest_order["id"] == payload["order_id"]
    assert latest_order["status"] == "accepted"
    assert len(latest_order["print_jobs"]) == 1
    assert latest_order["print_jobs"][0]["status"] == "pending"


def test_cash_checkout_survives_confirmation_email_failure(
    client, db_session: Session, admin_auth_headers, monkeypatch, caplog
):
    product = models.Product(
        name="Email Failure Pizza",
        price=11.0,
        category="Pizzas",
        description="Cash order item",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    def broken_confirmation_email(db, order, *, payment_method):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(
        "app.services.order_service.send_order_confirmation_email",
        broken_confirmation_email,
    )

    with caplog.at_level(logging.ERROR, logger="app.services.order_service"):
        response = client.post(
            "/orders/cash-checkout",
            json={**_order_payload(product.id), "payment_method": "cash"},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "accepted"
    assert "order_email_failed" in caplog.text

    admin_orders_response = client.get("/admin/orders", headers=admin_auth_headers)
    assert admin_orders_response.status_code == 200
    latest_order = admin_orders_response.json()[0]
    assert latest_order["id"] == payload["order_id"]
    assert latest_order["status"] == "accepted"
    assert len(latest_order["print_jobs"]) == 1
    assert latest_order["print_jobs"][0]["status"] == "pending"


def test_create_order_with_authenticated_user_stores_customer_email(client, db_session: Session):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "buyer@example.com",
            "password": "secret123",
        },
    )
    token = register_response.json()["access_token"]

    product = models.Product(
        name="Veg Pizza",
        price=10.5,
        category="Pizzas",
        description="Veggie",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post(
        "/orders",
        json={**_order_payload(product.id), "customer_email": "buyer@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    order_id = response.json()["order_id"]
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert order.customer_email == "buyer@example.com"


def test_create_order_rejects_missing_delivery_fields(client, db_session: Session):
    product = models.Product(name="Missing", price=7.0, category="Pizzas", description="X")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    payload = _order_payload(product.id)
    payload["delivery_address"] = " "

    response = client.post("/orders", json=payload)
    assert response.status_code in {400, 422}


def test_create_collection_order_skips_delivery_fee(client, db_session: Session):
    product = models.Product(
        name="Collection Pizza",
        price=10.0,
        category="Pizzas",
        description="X",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    payload = _order_payload(product.id)
    payload.update(
        {
            "fulfillment_method": "collection",
            "delivery_address": "",
            "delivery_city": "",
            "delivery_postal_code": "",
        }
    )

    response = client.post("/orders", json=payload)

    assert response.status_code == 201
    assert response.json()["total"] == 10.0
    order = db_session.get(models.Order, response.json()["order_id"])
    assert order is not None
    assert order.fulfillment_method == "collection"
    assert float(order.delivery_fee) == 0


def test_create_order_rejects_sold_out_product(client, db_session: Session):
    product = models.Product(
        name="Sold Out Pizza",
        price=12.0,
        category="Pizzas",
        description="N/A",
        is_available=False,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post("/orders", json=_order_payload(product.id))
    assert response.status_code == 400
    assert "sold out" in response.json()["detail"].lower()


def test_cash_checkout_rejects_sold_out_product(client, db_session: Session):
    product = models.Product(
        name="Sold Out Cash",
        price=11.0,
        category="Pizzas",
        description="N/A",
        is_available=False,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.post(
        "/orders/cash-checkout",
        json={**_order_payload(product.id), "payment_method": "cash"},
    )
    assert response.status_code == 400
    assert "sold out" in response.json()["detail"].lower()


def test_tracking_works_with_email_and_phone(client, db_session: Session):
    product = models.Product(name="Track", price=12.0, category="Pizzas", description="T")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create = client.post("/orders", json=_order_payload(product.id))
    order_id = create.json()["order_id"]

    email_response = client.get(f"/orders/{order_id}/tracking?email=client@example.com")
    assert email_response.status_code == 200
    assert email_response.json()["id"] == order_id
    assert email_response.json()["items"][0]["extras"] == ""

    phone_response = client.get(f"/orders/{order_id}/tracking?phone=0899730419")
    assert phone_response.status_code == 200
    assert phone_response.json()["id"] == order_id

    denied = client.get(f"/orders/{order_id}/tracking?email=wrong@example.com")
    assert denied.status_code == 404


def test_admin_orders_filters_status_and_payment(client, db_session: Session, admin_auth_headers):
    product = models.Product(name="Filter", price=10.0, category="Pizzas", description="F")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    created = client.post("/orders", json=_order_payload(product.id)).json()["order_id"]
    client.patch(
        f"/admin/orders/{created}/status",
        json={"status": "paid"},
        headers=admin_auth_headers,
    )

    cash_payload = {**_order_payload(product.id), "payment_method": "cash"}
    client.post("/orders/cash-checkout", json=cash_payload)

    paid = client.get("/admin/orders?status=paid", headers=admin_auth_headers)
    assert paid.status_code == 200
    assert all(order["status"] == "paid" for order in paid.json())

    cash = client.get("/admin/orders?payment_method=cash", headers=admin_auth_headers)
    assert cash.status_code == 200
    assert all(order["payment_method"] == "cash" for order in cash.json())


def test_admin_orders_filters_search_limit_offset_date(
    client, db_session: Session, admin_auth_headers
):
    product = models.Product(name="Searchable", price=9.0, category="Pizzas", description="S")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    first_payload = _order_payload(product.id)
    first_payload["customer_name"] = "Alice Walker"
    first_payload["customer_email"] = "alice@example.com"
    first_payload["customer_phone"] = "111111"
    first_id = client.post("/orders", json=first_payload).json()["order_id"]

    second_payload = _order_payload(product.id)
    second_payload["customer_name"] = "Bob Marley"
    second_payload["customer_email"] = "bob@example.com"
    second_payload["customer_phone"] = "222222"
    second_id = client.post("/orders", json=second_payload).json()["order_id"]

    by_phone = client.get("/admin/orders?search=222222", headers=admin_auth_headers)
    assert by_phone.status_code == 200
    assert len(by_phone.json()) == 1
    assert by_phone.json()[0]["id"] == second_id

    by_email = client.get("/admin/orders?search=alice@example.com", headers=admin_auth_headers)
    assert by_email.status_code == 200
    assert len(by_email.json()) == 1
    assert by_email.json()[0]["id"] == first_id

    by_id = client.get(f"/admin/orders?search={second_id}", headers=admin_auth_headers)
    assert by_id.status_code == 200
    assert len(by_id.json()) == 1
    assert by_id.json()[0]["id"] == second_id

    today = client.get("/admin/orders?date_from=2026-01-01", headers=admin_auth_headers)
    assert today.status_code == 200
    assert len(today.json()) >= 2

    limited = client.get("/admin/orders?limit=1&offset=0", headers=admin_auth_headers)
    assert limited.status_code == 200
    assert len(limited.json()) == 1
    next_page = client.get("/admin/orders?limit=1&offset=1", headers=admin_auth_headers)
    assert next_page.status_code == 200
    assert len(next_page.json()) == 1
    assert limited.json()[0]["id"] != next_page.json()[0]["id"]


def test_non_admin_cannot_access_admin_orders_filters(client, db_session: Session):
    first = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "secret123"},
    )
    assert first.status_code == 201

    register = client.post(
        "/auth/register",
        json={"email": "nonadmin@example.com", "password": "secret123"},
    )
    token = register.json()["access_token"]
    response = client.get(
        "/admin/orders?status=paid&search=alice",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_print_failed_visible_in_admin_orders(client, db_session: Session, admin_auth_headers):
    product = models.Product(name="Failure", price=10.0, category="Pizzas", description="X")
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    order_id = client.post("/orders", json=_order_payload(product.id)).json()["order_id"]
    client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "paid"},
        headers=admin_auth_headers,
    )
    client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=admin_auth_headers,
    )
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert order.print_jobs
    job = order.print_jobs[0]
    job.status = "failed"
    job.last_error = "No paper"
    db_session.commit()

    response = client.get("/admin/orders", headers=admin_auth_headers)
    assert response.status_code == 200
    target = next(item for item in response.json() if item["id"] == order_id)
    assert any(print_job["status"] == "failed" for print_job in target["print_jobs"])
