from sqlalchemy.orm import Session

from app.database import models


def _create_order_for_print_flow(client, db_session: Session, admin_auth_headers) -> int:
    product = models.Product(
        name="Family Deal",
        price=22.0,
        category="Family Deals",
        description="Large combo",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    create_response = client.post(
        "/orders",
        json={"items": [{"product_id": product.id, "quantity": 1, "extras": ""}]},
    )
    order_id = create_response.json()["order_id"]

    client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "paid"},
        headers=admin_auth_headers,
    )
    client.patch(
        f"/admin/orders/{order_id}/status",
        json={"status": "accepted"},
        headers=admin_auth_headers,
    )
    return order_id


def test_print_agent_pull_and_complete(
    client, db_session: Session, admin_auth_headers, monkeypatch
):
    monkeypatch.setattr("app.core.dependencies.PRINT_AGENT_KEY", "agent-secret")
    order_id = _create_order_for_print_flow(client, db_session, admin_auth_headers)

    pull_response = client.post(
        "/print-agent/jobs/pull",
        json={"agent_id": "kitchen-tablet-1"},
        headers={"X-Print-Agent-Key": "agent-secret"},
    )
    assert pull_response.status_code == 200

    job = pull_response.json()["job"]
    assert job is not None
    assert job["order"]["id"] == order_id
    assert job["attempt_count"] == 1

    complete_response = client.post(
        f"/print-agent/jobs/{job['job_id']}/complete",
        json={"agent_id": "kitchen-tablet-1"},
        headers={"X-Print-Agent-Key": "agent-secret"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "printed"

    orders_response = client.get("/admin/orders", headers=admin_auth_headers)
    assert orders_response.status_code == 200
    assert orders_response.json()[0]["status"] == "printed"


def test_print_agent_fail_marks_order_failed_after_last_attempt(
    client,
    db_session: Session,
    admin_auth_headers,
    monkeypatch,
):
    monkeypatch.setattr("app.core.dependencies.PRINT_AGENT_KEY", "agent-secret")
    monkeypatch.setattr("app.services.printing_service.PRINT_JOB_MAX_ATTEMPTS", 1)

    _create_order_for_print_flow(client, db_session, admin_auth_headers)

    pull_response = client.post(
        "/print-agent/jobs/pull",
        json={"agent_id": "kitchen-tablet-1"},
        headers={"X-Print-Agent-Key": "agent-secret"},
    )
    job_id = pull_response.json()["job"]["job_id"]

    fail_response = client.post(
        f"/print-agent/jobs/{job_id}/fail",
        json={
            "agent_id": "kitchen-tablet-1",
            "error": "No paper in printer",
        },
        headers={"X-Print-Agent-Key": "agent-secret"},
    )
    assert fail_response.status_code == 200
    assert fail_response.json()["status"] == "failed"

    orders_response = client.get("/admin/orders", headers=admin_auth_headers)
    assert orders_response.status_code == 200
    assert orders_response.json()[0]["status"] == "failed"


def test_admin_can_reprint_after_successful_print(
    client,
    db_session: Session,
    admin_auth_headers,
    monkeypatch,
):
    monkeypatch.setattr("app.core.dependencies.PRINT_AGENT_KEY", "agent-secret")
    order_id = _create_order_for_print_flow(client, db_session, admin_auth_headers)

    pull_response = client.post(
        "/print-agent/jobs/pull",
        json={"agent_id": "kitchen-tablet-1"},
        headers={"X-Print-Agent-Key": "agent-secret"},
    )
    job_id = pull_response.json()["job"]["job_id"]
    client.post(
        f"/print-agent/jobs/{job_id}/complete",
        json={"agent_id": "kitchen-tablet-1"},
        headers={"X-Print-Agent-Key": "agent-secret"},
    )

    reprint_response = client.post(
        f"/admin/orders/{order_id}/reprint",
        headers=admin_auth_headers,
    )
    assert reprint_response.status_code == 200
    assert reprint_response.json()["print_job"]["status"] == "pending"

    orders_response = client.get("/admin/orders", headers=admin_auth_headers)
    assert orders_response.status_code == 200
    assert orders_response.json()[0]["status"] == "accepted"
