from sqlalchemy.orm import Session

from app.database import models
from print_agent.agent import format_ticket


def _order_payload(product_id: int) -> dict:
    return {
        "items": [{"product_id": product_id, "quantity": 1, "extras": ""}],
        "customer_name": "Angel Client",
        "customer_email": "client@example.com",
        "customer_phone": "0899730419",
        "delivery_address": "Bastion Quay c33",
        "delivery_city": "Athlone",
        "delivery_postal_code": "N37XF78",
        "delivery_notes": "",
        "payment_method": "card",
        "delivery_fee": 2.5,
    }


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
        json=_order_payload(product.id),
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
    assert job["order"]["daily_order_number"] == 1
    assert job["order"]["customer_name"] == "Angel Client"
    assert job["order"]["customer_phone"] == "0899730419"
    assert job["order"]["delivery_address"] == "Bastion Quay c33"
    assert job["order"]["delivery_city"] == "Athlone"
    assert job["order"]["delivery_postal_code"] == "N37XF78"
    assert job["order"]["payment_method"] == "card"
    assert job["order"]["subtotal"] == 22.0
    assert job["order"]["delivery_fee"] == 2.5
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


def test_print_agent_ticket_contains_kitchen_details():
    ticket = format_ticket(
        {
            "job_id": 7,
            "attempt_count": 1,
            "max_attempts": 3,
            "order": {
                "id": 42,
                "daily_order_number": 3,
                "status": "printing",
                "customer_name": "Angel Client",
                "customer_email": "client@example.com",
                "customer_phone": "0899730419",
                "delivery_address": "Bastion Quay c33",
                "delivery_city": "Athlone",
                "delivery_postal_code": "N37XF78",
                "delivery_notes": "Ring bell twice",
                "payment_method": "cash",
                "subtotal": 22.0,
                "delivery_fee": 2.5,
                "total_price": 24.5,
                "created_at": "2026-06-10T20:35:00",
                "items": [
                    {
                        "product_id": 1,
                        "product_name": "Family Deal",
                        "quantity": 1,
                        "price": 22.0,
                        "extras": "extra cheese",
                    }
                ],
            },
        }
    )

    assert "Pizzeria Il Basilico" in ticket
    assert "===DELIVERY ORDER===" in ticket
    assert "D0003" in ticket
    assert "Ref:42" in ticket
    assert "CASH" in ticket
    assert "CUSTOMER" in ticket
    assert "Angel Client" in ticket
    assert "ADDRESS" in ticket
    assert "Bastion Quay c33" in ticket
    assert "NOTES" in ticket
    assert "Ring bell twice" in ticket
    assert "1 x FAMILY DEAL" in ticket
    assert "extra cheese" in ticket
    assert "Subtotal:" in ticket
    assert "€22.00" in ticket
    assert "Delivery Charge:" in ticket
    assert "TOTAL:" in ticket
    assert "€24.50" in ticket
    assert "In:" in ticket
    assert "Out:" in ticket
    assert "UNPAID" in ticket
    assert "System: Pizzeria App" in ticket


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
