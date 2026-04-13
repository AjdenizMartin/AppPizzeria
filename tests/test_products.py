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
