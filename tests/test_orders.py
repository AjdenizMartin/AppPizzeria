from sqlalchemy.orm import Session

from app.database import models


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
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                    "extras": "Extra cheese",
                }
            ]
        },
    )

    assert response.status_code == 201
    assert response.json() == {"order_id": 1, "total": 19.0, "status": "created"}


def test_create_order_rejects_empty_items(client):
    response = client.post("/orders", json={"items": []})

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
        json={"items": [{"product_id": product.id, "quantity": 1, "extras": ""}]},
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
        json={"items": [{"product_id": product.id, "quantity": 1, "extras": ""}]},
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
        json={"items": [{"product_id": product.id, "quantity": 2, "extras": ""}]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["total"] == 22.0
    assert payload["status"] == "accepted"
    assert payload["payment_method"] == "cash"

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
        json={"items": [{"product_id": product.id, "quantity": 1, "extras": ""}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    order_id = response.json()["order_id"]
    order = db_session.get(models.Order, order_id)
    assert order is not None
    assert order.customer_email == "buyer@example.com"
