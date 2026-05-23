from io import BytesIO

from sqlalchemy.orm import Session

from app.database import models


def test_get_products_returns_seeded_products(client, db_session: Session):
    db_session.add(
        models.Product(
            name="Margherita",
            price=11.5,
            category="Pizzas",
            description="Classic",
        )
    )
    db_session.commit()

    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Margherita",
            "description": "Classic",
            "price": 11.5,
            "category": "Pizzas",
            "image_url": None,
            "is_available": True,
            "is_active": True,
        }
    ]


def test_create_and_delete_product(client, admin_auth_headers):
    create_response = client.post(
        "/admin/products",
        data={
            "name": "Pepperoni",
            "price": "13.0",
            "category": "Pizzas",
            "description": "Spicy",
        },
        headers=admin_auth_headers,
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Pepperoni"
    assert created["image_url"] is None
    assert created["is_available"] is True
    assert created["is_active"] is True

    delete_response = client.delete(
        f"/admin/products/{created['id']}",
        headers=admin_auth_headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {"message": "Deleted"}

    list_response = client.get("/products")

    assert list_response.status_code == 200
    assert list_response.json() == []


def test_create_product_requires_admin_auth(client):
    response = client.post(
        "/admin/products",
        data={
            "name": "Unauthorized Pizza",
            "price": "10.0",
            "category": "Pizzas",
            "description": "No token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_update_product(client, admin_auth_headers):
    create_response = client.post(
        "/admin/products",
        data={
            "name": "Pepperoni",
            "price": "13.0",
            "category": "Pizzas",
            "description": "Spicy",
        },
        headers=admin_auth_headers,
    )
    product_id = create_response.json()["id"]

    update_response = client.put(
        f"/admin/products/{product_id}",
        data={
            "name": "Pepperoni XL",
            "price": "14.5",
            "category": "Highlights",
            "description": "Spicy and bigger",
        },
        headers=admin_auth_headers,
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Pepperoni XL"
    assert updated["price"] == 14.5
    assert updated["category"] == "Highlights"
    assert updated["description"] == "Spicy and bigger"
    assert updated["is_available"] is True
    assert updated["is_active"] is True


def test_admin_can_mark_product_as_sold_out(client, admin_auth_headers):
    create_response = client.post(
        "/admin/products",
        data={
            "name": "Pepperoni",
            "price": "13.0",
            "category": "Pizzas",
            "description": "Spicy",
        },
        headers=admin_auth_headers,
    )
    product_id = create_response.json()["id"]

    update_response = client.put(
        f"/admin/products/{product_id}",
        data={
            "name": "Pepperoni",
            "price": "13.0",
            "category": "Pizzas",
            "description": "Spicy",
            "is_available": "false",
        },
        headers=admin_auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_available"] is False


def test_non_admin_cannot_change_product_availability(client, admin_auth_headers):
    create_response = client.post(
        "/admin/products",
        data={
            "name": "Four Cheese",
            "price": "14.0",
            "category": "Pizzas",
            "description": "Cheesy",
        },
        headers=admin_auth_headers,
    )
    product_id = create_response.json()["id"]

    response = client.put(
        f"/admin/products/{product_id}",
        data={
            "name": "Four Cheese",
            "price": "14.0",
            "category": "Pizzas",
            "description": "Cheesy",
            "is_available": "false",
        },
    )
    assert response.status_code == 401


def test_update_product_requires_admin_auth(client, admin_auth_headers):
    create_response = client.post(
        "/admin/products",
        data={
            "name": "BBQ Burger",
            "price": "11.0",
            "category": "Burgers",
            "description": "Classic",
        },
        headers=admin_auth_headers,
    )
    product_id = create_response.json()["id"]

    update_response = client.put(
        f"/admin/products/{product_id}",
        data={
            "name": "BBQ Burger 2.0",
            "price": "12.0",
            "category": "Burgers",
            "description": "Updated",
        },
    )

    assert update_response.status_code == 401
    assert update_response.json() == {"detail": "Authentication required"}


def test_upload_invalid_type_rejected(client, admin_auth_headers):
    response = client.post(
        "/admin/products",
        data={"name": "Bad", "price": "10", "category": "Pizzas", "description": "x"},
        files={"file": ("bad.txt", BytesIO(b"hello"), "text/plain")},
        headers=admin_auth_headers,
    )
    assert response.status_code == 400


def test_upload_too_large_rejected(client, admin_auth_headers, monkeypatch):
    monkeypatch.setattr("app.services.file_service.MAX_PRODUCT_IMAGE_BYTES", 10)
    response = client.post(
        "/admin/products",
        data={"name": "Big", "price": "10", "category": "Pizzas", "description": "x"},
        files={"file": ("big.png", BytesIO(b"x" * 64), "image/png")},
        headers=admin_auth_headers,
    )
    assert response.status_code == 400


def test_upload_valid_image_accepted(client, admin_auth_headers):
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    response = client.post(
        "/admin/products",
        data={"name": "Img", "price": "10", "category": "Pizzas", "description": "x"},
        files={"file": ("ok.png", BytesIO(png_header), "image/png")},
        headers=admin_auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["image_url"] is not None


def test_product_with_order_history_is_archived_on_delete(
    client, db_session: Session, admin_auth_headers
):
    product = models.Product(name="Hist", price=12, category="Pizzas", description="x")
    db_session.add(product)
    db_session.flush()
    order = models.Order(
        status="created",
        customer_name="A",
        customer_email="a@a.com",
        customer_phone="123",
        delivery_address="x",
        delivery_city="y",
        delivery_postal_code="N1",
        payment_method="cash",
        delivery_fee=0,
        total_price=12,
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(
        models.OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            price=12,
            extras="",
        )
    )
    db_session.commit()

    response = client.delete(f"/admin/products/{product.id}", headers=admin_auth_headers)
    assert response.status_code == 200
    db_session.expire_all()
    stored = db_session.get(models.Product, product.id)
    assert stored is not None
    assert stored.is_active is False
    assert stored.is_available is False


def test_archived_product_not_in_public_menu(client, db_session: Session):
    product = models.Product(
        name="Archived",
        price=9,
        category="Pizzas",
        description="x",
        is_active=False,
        is_available=False,
    )
    db_session.add(product)
    db_session.commit()
    response = client.get("/products")
    assert response.status_code == 200
    assert response.json() == []


def test_admin_can_view_archived_products(client, db_session: Session, admin_auth_headers):
    product = models.Product(
        name="Archived", price=9, category="Pizzas", description="x", is_active=False
    )
    db_session.add(product)
    db_session.commit()
    response = client.get("/admin/products?include_inactive=true", headers=admin_auth_headers)
    assert response.status_code == 200
    assert any(row["id"] == product.id for row in response.json())


def test_non_admin_cannot_archive_restore_product(client, admin_auth_headers):
    created = client.post(
        "/admin/products",
        data={"name": "X", "price": "10", "category": "Pizzas", "description": "x"},
        headers=admin_auth_headers,
    )
    product_id = created.json()["id"]
    response = client.patch(f"/admin/products/{product_id}/archive", data={"archived": "true"})
    assert response.status_code == 401
