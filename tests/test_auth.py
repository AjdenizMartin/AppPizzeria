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
    }
