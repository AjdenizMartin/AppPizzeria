from datetime import UTC, datetime

from app.database import models


def _mk_order(
    db_session,
    *,
    order_id: int,
    status: str,
    payment_method: str,
    total: float,
    created_at: datetime,
    item_name: str,
    item_qty: int,
    item_price: float,
):
    order = models.Order(
        id=order_id,
        status=status,
        payment_method=payment_method,
        total_price=total,
        customer_name="Client",
        customer_email="client@example.com",
        customer_phone="111",
        delivery_address="Addr",
        delivery_city="City",
        delivery_postal_code="X1",
        delivery_fee=0,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        models.OrderItem(
            order_id=order.id,
            product_id=order_id,
            product_name=item_name,
            quantity=item_qty,
            price=item_price,
            extras="",
        )
    )


def test_daily_report_calculates_revenue_and_excludes_cancelled(
    client, db_session, admin_auth_headers
):
    date = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)
    _mk_order(
        db_session,
        order_id=1,
        status="accepted",
        payment_method="cash",
        total=20,
        created_at=date,
        item_name="Margherita",
        item_qty=2,
        item_price=10,
    )
    _mk_order(
        db_session,
        order_id=2,
        status="delivered",
        payment_method="card",
        total=30,
        created_at=date,
        item_name="Pepperoni",
        item_qty=3,
        item_price=10,
    )
    _mk_order(
        db_session,
        order_id=3,
        status="cancelled",
        payment_method="card",
        total=99,
        created_at=date,
        item_name="Cancelled",
        item_qty=1,
        item_price=99,
    )
    db_session.commit()

    response = client.get("/admin/reports/sales?date=2026-05-04", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_orders"] == 3
    assert data["cancelled_orders"] == 1
    assert data["paid_or_completed_orders"] == 2
    assert data["revenue_total"] == 50.0
    assert data["cash_total"] == 20.0
    assert data["card_total"] == 30.0
    assert data["average_ticket"] == 25.0


def test_daily_report_top_products_and_total_items(client, db_session, admin_auth_headers):
    date = datetime(2026, 5, 4, 12, 0, tzinfo=UTC)
    _mk_order(
        db_session,
        order_id=10,
        status="accepted",
        payment_method="cash",
        total=40,
        created_at=date,
        item_name="Hawaiian",
        item_qty=4,
        item_price=10,
    )
    _mk_order(
        db_session,
        order_id=11,
        status="paid",
        payment_method="card",
        total=20,
        created_at=date,
        item_name="Margherita",
        item_qty=2,
        item_price=10,
    )
    db_session.commit()

    response = client.get("/admin/reports/sales?date=2026-05-04", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_items_sold"] == 6
    assert len(data["top_products"]) == 2
    assert data["top_products"][0]["product_name"] == "Hawaiian"
    assert data["top_products"][0]["quantity_sold"] == 4


def test_daily_report_empty_day_returns_zeros(client, admin_auth_headers):
    response = client.get("/admin/reports/sales?date=2026-05-04", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_orders"] == 0
    assert data["paid_or_completed_orders"] == 0
    assert data["cancelled_orders"] == 0
    assert data["revenue_total"] == 0.0
    assert data["cash_total"] == 0.0
    assert data["card_total"] == 0.0
    assert data["average_ticket"] == 0.0
    assert data["total_items_sold"] == 0
    assert data["top_products"] == []


def test_non_admin_cannot_access_sales_report(client):
    response = client.get("/admin/reports/sales?date=2026-05-04")
    assert response.status_code == 401

    admin_bootstrap = client.post(
        "/auth/register",
        json={"email": "bootstrap-admin@example.com", "password": "secret123"},
    )
    assert admin_bootstrap.status_code == 201

    register = client.post(
        "/auth/register",
        json={"email": "nonadmin-report@example.com", "password": "secret123"},
    )
    token = register.json()["access_token"]
    denied = client.get(
        "/admin/reports/sales?date=2026-05-04",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 403
