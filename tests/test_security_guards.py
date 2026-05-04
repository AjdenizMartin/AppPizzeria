import app.main as main_module


def test_production_rejects_auto_create_tables(monkeypatch):
    monkeypatch.setattr(main_module, "APP_ENV", "production")
    monkeypatch.setattr(main_module, "AUTO_CREATE_TABLES", True)

    try:
        main_module._validate_startup_configuration()
    except RuntimeError as exc:
        assert "AUTO_CREATE_TABLES" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for insecure production startup config")
