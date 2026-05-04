import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "app" / "static"
PRODUCT_IMAGES_DIR = STATIC_DIR / "images"

_frontend_dist_dir = BASE_DIR / "frontend-react" / "dist"
FRONTEND_DIR = (
    Path(os.getenv("FRONTEND_DIR")).resolve()
    if os.getenv("FRONTEND_DIR")
    else _frontend_dist_dir
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pizzeria.db").strip()
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173").rstrip("/")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me").strip()
TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
STRIPE_KEY = (os.getenv("STRIPE_KEY") or "").strip()
STRIPE_WEBHOOK_SECRET = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
PRINT_AGENT_KEY = (os.getenv("PRINT_AGENT_KEY") or "").strip()
PRINT_JOB_MAX_ATTEMPTS = int(os.getenv("PRINT_JOB_MAX_ATTEMPTS", "3"))
PRINT_FAILURE_ALERT_THRESHOLD = int(os.getenv("PRINT_FAILURE_ALERT_THRESHOLD", "3"))
ERROR_RATE_ALERT_THRESHOLD = float(os.getenv("ERROR_RATE_ALERT_THRESHOLD", "5.0"))
CRITICAL_EVENTS_HISTORY_LIMIT = int(os.getenv("CRITICAL_EVENTS_HISTORY_LIMIT", "100"))
SMTP_HOST = (os.getenv("SMTP_HOST") or "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = (os.getenv("SMTP_USER") or "").strip()
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD") or "").strip()
SMTP_FROM_EMAIL = (os.getenv("SMTP_FROM_EMAIL") or SMTP_USER or "no-reply@pizzeria.local").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip()
}

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", FRONTEND_BASE_URL).split(",")
    if origin.strip()
]
if not CORS_ORIGINS:
    CORS_ORIGINS = [FRONTEND_BASE_URL]

DEFAULT_SECRET_KEY = "dev-secret-key-change-me"


def validate_production_config() -> None:
    if APP_ENV != "production":
        return

    errors: list[str] = []
    if AUTO_CREATE_TABLES:
        errors.append("AUTO_CREATE_TABLES must be false in production")
    if not SECRET_KEY or SECRET_KEY == DEFAULT_SECRET_KEY:
        errors.append("SECRET_KEY must be set to a non-default value in production")
    if not STRIPE_KEY:
        errors.append("STRIPE_KEY is required in production")
    if not STRIPE_WEBHOOK_SECRET:
        errors.append("STRIPE_WEBHOOK_SECRET is required in production")
    if not PRINT_AGENT_KEY:
        errors.append("PRINT_AGENT_KEY is required in production")
    if DATABASE_URL.startswith("sqlite"):
        errors.append("DATABASE_URL must not use sqlite in production")
    if FRONTEND_BASE_URL.startswith("http://127.0.0.1") or FRONTEND_BASE_URL.startswith(
        "http://localhost"
    ):
        errors.append("FRONTEND_BASE_URL must not be localhost in production")
    if any(origin.strip() == "*" for origin in CORS_ORIGINS):
        errors.append("CORS_ORIGINS must not contain wildcard '*' in production")

    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))
