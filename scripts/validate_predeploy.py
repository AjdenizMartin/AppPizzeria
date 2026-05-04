import os
import sys


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    auto_create_tables = _as_bool(os.getenv("AUTO_CREATE_TABLES", "true"))
    stripe_webhook_secret = (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()
    secret_key = (os.getenv("SECRET_KEY") or "").strip()
    cors_origins = (os.getenv("CORS_ORIGINS") or "").strip()

    errors: list[str] = []

    if app_env == "production":
        if auto_create_tables:
            errors.append("AUTO_CREATE_TABLES must be false in production")
        if not stripe_webhook_secret:
            errors.append("STRIPE_WEBHOOK_SECRET is required in production")
        if not secret_key or secret_key == "dev-secret-key-change-me":
            errors.append("SECRET_KEY must be set to a non-default value in production")
        if not cors_origins:
            errors.append("CORS_ORIGINS must be configured in production")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print("[OK] pre-deploy configuration validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
