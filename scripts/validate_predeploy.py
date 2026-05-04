import os
import sys

DEFAULT_SECRET_KEY = "dev-secret-key-change-me"


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_localhost(value: str) -> bool:
    normalized = value.strip().lower()
    return "127.0.0.1" in normalized or "localhost" in normalized


def main() -> int:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    auto_create_tables = _as_bool(os.getenv("AUTO_CREATE_TABLES", "true"))
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    frontend_base_url = (os.getenv("FRONTEND_BASE_URL") or "").strip()
    cors_origins_raw = (os.getenv("CORS_ORIGINS") or "").strip()
    secret_key = (os.getenv("SECRET_KEY") or "").strip()
    stripe_key = (os.getenv("STRIPE_KEY") or "").strip()
    stripe_webhook_secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    print_agent_key = (os.getenv("PRINT_AGENT_KEY") or "").strip()

    errors: list[str] = []

    if app_env != "production":
        errors.append("APP_ENV must be 'production' for predeploy validation")

    if not database_url:
        errors.append("DATABASE_URL is required")
    elif database_url.startswith("sqlite"):
        errors.append("DATABASE_URL must not be sqlite in production")

    if auto_create_tables:
        errors.append("AUTO_CREATE_TABLES must be false in production")

    if not frontend_base_url:
        errors.append("FRONTEND_BASE_URL is required")
    elif _is_localhost(frontend_base_url):
        errors.append("FRONTEND_BASE_URL must not point to localhost/127.0.0.1")

    if not cors_origins_raw:
        errors.append("CORS_ORIGINS is required in production")
    else:
        origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
        if any(origin == "*" for origin in origins):
            errors.append("CORS_ORIGINS must not contain wildcard '*' in production")
        if any(_is_localhost(origin) for origin in origins):
            errors.append("CORS_ORIGINS must not include localhost/127.0.0.1 in production")

    if not secret_key or secret_key == DEFAULT_SECRET_KEY:
        errors.append("SECRET_KEY must be set to a strong non-default value")

    if not stripe_key:
        errors.append("STRIPE_KEY is required")

    if not stripe_webhook_secret:
        errors.append("STRIPE_WEBHOOK_SECRET is required")

    if not print_agent_key:
        errors.append("PRINT_AGENT_KEY is required")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print("[OK] pre-deploy configuration validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
