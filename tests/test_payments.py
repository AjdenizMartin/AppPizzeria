def test_checkout_returns_url(client, monkeypatch):
    def fake_create_checkout(items, *, order_id=None):
        assert len(items) == 1
        assert items[0].name == "Pizza test"
        assert order_id == 7
        return "https://example.com/checkout"

    monkeypatch.setattr("app.routers.payments.create_checkout", fake_create_checkout)

    response = client.post(
        "/create-checkout-session",
        json={
            "items": [
                {
                    "name": "Pizza test",
                    "price": 12.5,
                    "quantity": 1,
                }
            ],
            "order_id": 7,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"url": "https://example.com/checkout"}


def test_checkout_rejects_empty_items(client):
    response = client.post("/create-checkout-session", json={"items": []})

    assert response.status_code == 400
    assert response.json() == {"detail": "No items provided"}
