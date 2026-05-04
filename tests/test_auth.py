def test_first_registered_user_becomes_admin(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "owner@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "owner@example.com"
    assert payload["user"]["is_admin"] is True
    assert payload["user"]["full_name"] is None
    assert payload["user"]["address_line"] is None
    assert payload["user"]["city"] is None
    assert payload["user"]["postal_code"] is None
    assert payload["user"]["phone"] is None


def test_login_and_me_flow(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "owner@example.com",
            "password": "secret123",
        },
    )
    token = register_response.json()["access_token"]

    login_response = client.post(
        "/auth/login",
        json={
            "email": "owner@example.com",
            "password": "secret123",
        },
    )

    assert login_response.status_code == 200

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": 1,
        "email": "owner@example.com",
        "is_admin": True,
        "full_name": None,
        "address_line": None,
        "city": None,
        "postal_code": None,
        "phone": None,
    }


def test_update_my_profile(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "customer@example.com",
            "password": "secret123",
        },
    )
    token = register_response.json()["access_token"]

    update_response = client.patch(
        "/auth/me/profile",
        json={
            "full_name": "Jane Customer",
            "address_line": "12 Market Street",
            "city": "Dublin",
            "postal_code": "D01X2Y3",
            "phone": "+353850000000",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Jane Customer"
    assert update_response.json()["address_line"] == "12 Market Street"
    assert update_response.json()["city"] == "Dublin"
    assert update_response.json()["postal_code"] == "D01X2Y3"
    assert update_response.json()["phone"] == "+353850000000"


def test_update_profile_requires_auth(client):
    response = client.patch(
        "/auth/me/profile",
        json={
            "full_name": "No Auth",
            "address_line": "1 Main St",
            "city": "Cork",
            "postal_code": "T12",
            "phone": "+3531",
        },
    )

    assert response.status_code == 401


def test_register_stores_initial_profile_fields(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "profiled@example.com",
            "password": "secret123",
            "full_name": "Jane Customer",
            "address_line": "12 Market Street",
            "city": "Dublin",
            "postal_code": "D01X2Y3",
            "phone": "+353850000000",
        },
    )

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["full_name"] == "Jane Customer"
    assert user["address_line"] == "12 Market Street"
    assert user["city"] == "Dublin"
    assert user["postal_code"] == "D01X2Y3"
    assert user["phone"] == "+353850000000"


def test_first_registered_user_is_not_admin_in_production(client, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.APP_ENV", "production")

    response = client.post(
        "/auth/register",
        json={
            "email": "prod-owner@example.com",
            "password": "secret123",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["is_admin"] is False


def test_register_rejects_invalid_email(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "secret123",
        },
    )

    assert response.status_code == 422
