import app.main as main_module
from app.core import config as config_module


def test_production_rejects_auto_create_tables(monkeypatch):
    monkeypatch.setattr(main_module, "APP_ENV", "production")
    monkeypatch.setattr(main_module, "AUTO_CREATE_TABLES", True)

    try:
        main_module._validate_startup_configuration()
    except RuntimeError as exc:
        assert "AUTO_CREATE_TABLES" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for insecure production startup config")


def test_production_rejects_default_secret_key(monkeypatch):
    monkeypatch.setattr(config_module, "APP_ENV", "production")
    monkeypatch.setattr(config_module, "AUTO_CREATE_TABLES", False)
    monkeypatch.setattr(config_module, "SECRET_KEY", "dev-secret-key-change-me")
    monkeypatch.setattr(config_module, "STRIPE_KEY", "sk_live_x")
    monkeypatch.setattr(config_module, "STRIPE_WEBHOOK_SECRET", "whsec_x")
    monkeypatch.setattr(config_module, "PRINT_AGENT_KEY", "print_x")
    monkeypatch.setattr(config_module, "DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setattr(config_module, "FRONTEND_BASE_URL", "https://app.example.com")
    monkeypatch.setattr(config_module, "CORS_ORIGINS", ["https://app.example.com"])

    try:
        config_module.validate_production_config()
    except RuntimeError as exc:
        assert "SECRET_KEY" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for default SECRET_KEY in production")


def test_production_requires_stripe_webhook_secret(monkeypatch):
    monkeypatch.setattr(config_module, "APP_ENV", "production")
    monkeypatch.setattr(config_module, "AUTO_CREATE_TABLES", False)
    monkeypatch.setattr(config_module, "SECRET_KEY", "real-secret")
    monkeypatch.setattr(config_module, "STRIPE_KEY", "sk_live_x")
    monkeypatch.setattr(config_module, "STRIPE_WEBHOOK_SECRET", "")
    monkeypatch.setattr(config_module, "PRINT_AGENT_KEY", "print_x")
    monkeypatch.setattr(config_module, "DATABASE_URL", "postgresql://user:pass@host/db")
    monkeypatch.setattr(config_module, "FRONTEND_BASE_URL", "https://app.example.com")
    monkeypatch.setattr(config_module, "CORS_ORIGINS", ["https://app.example.com"])

    try:
        config_module.validate_production_config()
    except RuntimeError as exc:
        assert "STRIPE_WEBHOOK_SECRET" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing STRIPE_WEBHOOK_SECRET")
