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
    assert response.json() == {"order_id": 1, "total": 19.0}


def test_create_order_rejects_empty_items(client):
    response = client.post("/orders", json={"items": []})

    assert response.status_code == 400
    assert response.json() == {"detail": "No items provided"}
