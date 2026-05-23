from app.core.security import decode_access_token
from app.database import models


def _register(client, email: str):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "secret123"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return response.json()["user"], {"Authorization": f"Bearer {token}"}, token


def test_jwt_includes_role(client):
    user, _headers, token = _register(client, "rolejwt@example.com")
    payload = decode_access_token(token)
    assert payload["role"] == user["role"]


def test_customer_cannot_access_admin_orders(client):
    _owner, _owner_headers, _ = _register(client, "owner-role@example.com")
    _customer, customer_headers, _ = _register(client, "customer-role@example.com")
    response = client.get("/admin/orders", headers=customer_headers)
    assert response.status_code == 403


def test_staff_can_access_orders_not_settings(client, db_session, admin_auth_headers):
    created = client.post(
        "/auth/register",
        json={"email": "staff@example.com", "password": "secret123"},
    )
    staff_id = created.json()["user"]["id"]
    client.patch(
        f"/auth/admin/users/{staff_id}/role",
        json={"role": "staff"},
        headers=admin_auth_headers,
    )
    login = client.post("/auth/login", json={"email": "staff@example.com", "password": "secret123"})
    staff_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    ok = client.get("/admin/orders", headers=staff_headers)
    denied = client.get("/admin/restaurant/settings", headers=staff_headers)
    assert ok.status_code == 200
    assert denied.status_code == 403


def test_manager_can_access_products_and_reports(client, admin_auth_headers):
    created = client.post(
        "/auth/register",
        json={"email": "manager@example.com", "password": "secret123"},
    )
    manager_id = created.json()["user"]["id"]
    client.patch(
        f"/auth/admin/users/{manager_id}/role",
        json={"role": "manager"},
        headers=admin_auth_headers,
    )
    login = client.post(
        "/auth/login",
        json={"email": "manager@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    products = client.get("/admin/products", headers=headers)
    reports = client.get("/admin/reports/sales?date=2026-01-01", headers=headers)
    assert products.status_code == 200
    assert reports.status_code == 200


def test_owner_can_access_everything(client, admin_auth_headers):
    assert client.get("/admin/products", headers=admin_auth_headers).status_code == 200
    assert client.get("/admin/orders", headers=admin_auth_headers).status_code == 200
    assert client.get("/admin/restaurant/settings", headers=admin_auth_headers).status_code == 200


def test_legacy_admin_keeps_access(client, db_session):
    legacy = models.User(email="legacy@example.com", hashed_password="x", is_admin=True, role="")
    db_session.add(legacy)
    db_session.commit()

    from app.core.security import create_access_token

    token = create_access_token(
        subject=str(legacy.id),
        email=legacy.email,
        is_admin=True,
        role="owner",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/admin/orders", headers=headers)
    assert response.status_code == 200


def test_sensitive_endpoint_rejects_insufficient_role(client, admin_auth_headers):
    created = client.post(
        "/auth/register",
        json={"email": "staff2@example.com", "password": "secret123"},
    )
    staff_id = created.json()["user"]["id"]
    client.patch(
        f"/auth/admin/users/{staff_id}/role",
        json={"role": "staff"},
        headers=admin_auth_headers,
    )
    login = client.post(
        "/auth/login",
        json={"email": "staff2@example.com", "password": "secret123"},
    )
    staff_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.patch(
        "/admin/restaurant/settings",
        json={"restaurant_name": "X"},
        headers=staff_headers,
    )
    assert response.status_code == 403
