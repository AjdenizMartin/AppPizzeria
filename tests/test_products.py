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
