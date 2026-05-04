from app.core.observability import log_business_event


def test_metrics_endpoint_includes_operational_fields(client, admin_auth_headers):
    response = client.get("/metrics", headers=admin_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert "total_requests" in payload
    assert "total_errors" in payload
    assert "average_latency_ms" in payload
    assert "status_codes" in payload
    assert "business_events" in payload
    assert "recent_critical_events" in payload
    assert "alerts" in payload
    assert "stats" in payload


def test_metrics_prometheus_includes_business_events_counter(client, admin_auth_headers):
    log_business_event(event="order_created")

    response = client.get("/metrics/prometheus", headers=admin_auth_headers)

    assert response.status_code == 200
    assert "# HELP app_business_events_total" in response.text
    assert 'app_business_events_total{event="order_created"}' in response.text


def test_ops_status_raises_alert_for_print_failures(client, admin_auth_headers):
    log_business_event(event="print_job_failed", message="no paper")
    log_business_event(event="print_job_failed", message="paper jam")
    log_business_event(event="print_job_failed", message="offline printer")

    response = client.get("/ops/status", headers=admin_auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"yellow", "red"}
    assert "print_failures_high" in payload["alerts"]
    assert payload["stats"]["print_failures"] >= 3
    assert len(payload["recent_critical_events"]) >= 1


def test_admin_can_reset_metrics(client, admin_auth_headers):
    log_business_event(event="order_created")

    reset_response = client.post("/admin/metrics/reset", headers=admin_auth_headers)
    assert reset_response.status_code == 200
    assert reset_response.json()["ok"] is True

    metrics_response = client.get("/metrics", headers=admin_auth_headers)
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["business_events"] == {}
    assert payload["total_errors"] == 0


def test_admin_can_list_recent_operational_events(client, admin_auth_headers):
    log_business_event(event="print_job_failed", message="paper out")
    log_business_event(event="print_job_failed", message="offline")

    response = client.get(
        "/admin/metrics/events?event=print_job_failed&limit=5",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert all(item["event"] == "print_job_failed" for item in payload["events"])


def test_metrics_require_admin_auth(client):
    response = client.get("/metrics")
    assert response.status_code in {401, 403}


def test_ops_status_requires_admin_auth(client):
    response = client.get("/ops/status")
    assert response.status_code in {401, 403}
