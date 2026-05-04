import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import (
    APP_ENV,
    AUTO_CREATE_TABLES,
    CORS_ORIGINS,
    DATABASE_URL,
    ERROR_RATE_ALERT_THRESHOLD,
    FRONTEND_DIR,
    PRINT_FAILURE_ALERT_THRESHOLD,
    STATIC_DIR,
)
from app.core.dependencies import get_current_admin
from app.core.limiter import limiter
from app.core.observability import (
    build_request_log_line,
    create_request_id,
    format_prometheus_metrics,
    metrics,
    now_ms,
)
from app.database import models
from app.database.database import engine, ensure_runtime_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
SENSITIVE_OBSERVABILITY_PATHS = {"/metrics", "/metrics/prometheus", "/ops/status"}
FRONTEND_BUILD_READY = FRONTEND_DIR.is_dir() and (FRONTEND_DIR / "index.html").is_file()


class SPAStaticFiles(StaticFiles):
    def lookup_path(self, path: str):
        full_path, stat_result = super().lookup_path(path)
        if stat_result is None:
            return super().lookup_path("index.html")
        return full_path, stat_result


def _build_operational_alerts() -> tuple[list[str], dict[str, float]]:
    snapshot = metrics.snapshot()
    total_requests = max(1, snapshot.total_requests)
    error_rate = (snapshot.total_errors / total_requests) * 100
    print_failures = snapshot.business_events.get("print_job_failed", 0)

    alerts: list[str] = []
    if print_failures >= PRINT_FAILURE_ALERT_THRESHOLD:
        alerts.append("print_failures_high")
    if error_rate >= ERROR_RATE_ALERT_THRESHOLD:
        alerts.append("error_rate_high")

    stats = {
        "print_failures": float(print_failures),
        "error_rate_percent": round(error_rate, 2),
    }
    return alerts, stats


def _validate_startup_configuration() -> None:
    if APP_ENV == "production" and AUTO_CREATE_TABLES:
        raise RuntimeError(
            "Unsafe configuration: AUTO_CREATE_TABLES must be false in production"
        )


_validate_startup_configuration()

if AUTO_CREATE_TABLES:
    models.Base.metadata.create_all(bind=engine)

if DATABASE_URL.startswith("sqlite"):
    ensure_runtime_schema()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Pizzeria API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Stripe-Signature"],
)

app.include_router(api_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    request.state.request_id = create_request_id()
    start_ms = now_ms()
    metrics.request_started()

    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001
        latency_ms = now_ms() - start_ms
        metrics.request_finished(status_code=500, latency_ms=latency_ms)
        metrics.record_critical_event("request_failed", request.url.path)
        logger.exception(
            "request_failed %s",
            build_request_log_line(request=request, status_code=500, latency_ms=latency_ms),
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    response.headers["X-Request-ID"] = request.state.request_id
    latency_ms = now_ms() - start_ms
    metrics.request_finished(status_code=response.status_code, latency_ms=latency_ms)

    if request.url.path in SENSITIVE_OBSERVABILITY_PATHS and response.status_code in {401, 403}:
        logger.warning(
            "unauthorized_observability_access path=%s status=%s request_id=%s",
            request.url.path,
            response.status_code,
            request.state.request_id,
        )
        metrics.record_critical_event(
            "unauthorized_observability_access",
            f"path={request.url.path} status={response.status_code}",
        )

    logger.info(
        "request_completed %s",
        build_request_log_line(
            request=request,
            status_code=response.status_code,
            latency_ms=latency_ms,
        ),
    )
    return response


@app.get("/", include_in_schema=False)
def root():
    if FRONTEND_BUILD_READY:
        return FileResponse(FRONTEND_DIR / "index.html")
    return {"status": "ok", "message": "Pizzeria API is running"}


@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
def legacy_frontend_redirect(path: str = ""):
    target = f"/{path}".rstrip("/") if path else "/"
    if not target:
        target = "/"
    return RedirectResponse(url=target)


@app.get("/health", tags=["health"])
def health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "healthy"}


@app.get("/metrics", tags=["health"])
def metrics_read(_current_admin=Depends(get_current_admin)):
    snapshot = metrics.snapshot()
    alerts, stats = _build_operational_alerts()

    return {
        "total_requests": snapshot.total_requests,
        "total_errors": snapshot.total_errors,
        "in_flight_requests": snapshot.in_flight_requests,
        "average_latency_ms": round(snapshot.average_latency_ms, 2),
        "status_codes": snapshot.status_codes,
        "business_events": snapshot.business_events,
        "recent_critical_events": snapshot.recent_critical_events,
        "alerts": alerts,
        "stats": stats,
    }


@app.get("/metrics/prometheus", tags=["health"], response_class=PlainTextResponse)
def metrics_prometheus(_current_admin=Depends(get_current_admin)):
    snapshot = metrics.snapshot()
    payload = format_prometheus_metrics(snapshot)
    return PlainTextResponse(content=payload, media_type="text/plain; version=0.0.4")


@app.get("/ops/status", tags=["health"])
def operational_status(_current_admin=Depends(get_current_admin)):
    snapshot = metrics.snapshot()
    alerts, stats = _build_operational_alerts()

    status = "green"
    if alerts:
        status = "yellow"
    severe_error_rate = ERROR_RATE_ALERT_THRESHOLD * 2
    if "error_rate_high" in alerts and stats["error_rate_percent"] >= severe_error_rate:
        status = "red"

    return {
        "status": status,
        "alerts": alerts,
        "stats": stats,
        "recent_critical_events": snapshot.recent_critical_events,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if FRONTEND_BUILD_READY:
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
