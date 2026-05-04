import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from fastapi import Request

from app.core.config import CRITICAL_EVENTS_HISTORY_LIMIT

logger = logging.getLogger("app.request")
audit_logger = logging.getLogger("app.audit")


@dataclass
class MetricsSnapshot:
    total_requests: int
    total_errors: int
    in_flight_requests: int
    average_latency_ms: float
    status_codes: dict[str, int]
    business_events: dict[str, int]
    recent_critical_events: list[dict[str, str]]


class InMemoryMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._total_requests = 0
        self._total_errors = 0
        self._in_flight_requests = 0
        self._total_latency_ms = 0.0
        self._status_codes: dict[str, int] = {}
        self._business_events: dict[str, int] = {}
        maxlen = max(10, CRITICAL_EVENTS_HISTORY_LIMIT)
        self._recent_critical_events: deque[dict[str, str]] = deque(maxlen=maxlen)

    def request_started(self) -> None:
        with self._lock:
            self._in_flight_requests += 1

    def request_finished(self, *, status_code: int, latency_ms: float) -> None:
        with self._lock:
            self._total_requests += 1
            self._in_flight_requests = max(0, self._in_flight_requests - 1)
            self._total_latency_ms += latency_ms
            code_key = str(status_code)
            self._status_codes[code_key] = self._status_codes.get(code_key, 0) + 1
            if status_code >= 500:
                self._total_errors += 1

    def record_unhandled_error(self) -> None:
        with self._lock:
            self._total_errors += 1

    def record_business_event(self, event: str) -> None:
        with self._lock:
            self._business_events[event] = self._business_events.get(event, 0) + 1

    def record_critical_event(self, event: str, detail: str) -> None:
        with self._lock:
            self._recent_critical_events.appendleft(
                {
                    "event": event,
                    "detail": detail,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            avg_latency = 0.0
            if self._total_requests > 0:
                avg_latency = self._total_latency_ms / self._total_requests
            return MetricsSnapshot(
                total_requests=self._total_requests,
                total_errors=self._total_errors,
                in_flight_requests=self._in_flight_requests,
                average_latency_ms=avg_latency,
                status_codes=dict(self._status_codes),
                business_events=dict(self._business_events),
                recent_critical_events=list(self._recent_critical_events),
            )

    def reset(self) -> None:
        with self._lock:
            self._total_requests = 0
            self._total_errors = 0
            self._in_flight_requests = 0
            self._total_latency_ms = 0.0
            self._status_codes.clear()
            self._business_events.clear()
            self._recent_critical_events.clear()


metrics = InMemoryMetrics()


def build_request_log_line(*, request: Request, status_code: int, latency_ms: float) -> str:
    return (
        f"method={request.method} path={request.url.path} status={status_code} "
        f"latency_ms={latency_ms:.2f} request_id={request.state.request_id}"
    )


def create_request_id() -> str:
    return uuid.uuid4().hex


def now_ms() -> float:
    return time.perf_counter() * 1000


def format_prometheus_metrics(snapshot: MetricsSnapshot) -> str:
    lines = [
        "# HELP app_requests_total Total HTTP requests handled.",
        "# TYPE app_requests_total counter",
        f"app_requests_total {snapshot.total_requests}",
        "# HELP app_request_errors_total Total HTTP requests with 5xx status.",
        "# TYPE app_request_errors_total counter",
        f"app_request_errors_total {snapshot.total_errors}",
        "# HELP app_requests_in_flight Current in-flight HTTP requests.",
        "# TYPE app_requests_in_flight gauge",
        f"app_requests_in_flight {snapshot.in_flight_requests}",
        "# HELP app_request_latency_average_ms Average HTTP latency in milliseconds.",
        "# TYPE app_request_latency_average_ms gauge",
        f"app_request_latency_average_ms {snapshot.average_latency_ms:.2f}",
        "# HELP app_response_status_total Total responses by HTTP status code.",
        "# TYPE app_response_status_total counter",
    ]

    for status_code, count in sorted(snapshot.status_codes.items()):
        lines.append(f'app_response_status_total{{status_code="{status_code}"}} {count}')

    lines.extend(
        [
            "# HELP app_business_events_total Total business events by event name.",
            "# TYPE app_business_events_total counter",
        ]
    )
    for event_name, count in sorted(snapshot.business_events.items()):
        lines.append(f'app_business_events_total{{event="{event_name}"}} {count}')

    return "\n".join(lines) + "\n"


def log_business_event(
    *,
    event: str,
    request: Request | None = None,
    order_id: int | None = None,
    payment_method: str | None = None,
    print_job_id: int | None = None,
    status: str | None = None,
    message: str | None = None,
) -> None:
    metrics.record_business_event(event)
    request_id = getattr(getattr(request, "state", None), "request_id", "n/a")
    parts = [f"event={event}", f"request_id={request_id}"]

    if order_id is not None:
        parts.append(f"order_id={order_id}")
    if payment_method is not None:
        parts.append(f"payment_method={payment_method}")
    if print_job_id is not None:
        parts.append(f"print_job_id={print_job_id}")
    if status is not None:
        parts.append(f"status={status}")
    if message is not None:
        parts.append(f"message={message}")

    if event in {"print_job_failed"}:
        metrics.record_critical_event(event, message or "print job failed")

    audit_logger.info(" ".join(parts))
