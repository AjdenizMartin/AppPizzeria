import importlib


def test_database_engine_non_sqlite_avoids_check_same_thread(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/pizzeria")
    monkeypatch.setattr("dotenv.load_dotenv", lambda override=True: None)

    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs

        class DummyEngine:
            pass

        return DummyEngine()

    monkeypatch.setattr("sqlalchemy.create_engine", fake_create_engine)

    import app.core.config as config_module

    importlib.reload(config_module)

    import app.database.database as database_module

    importlib.reload(database_module)

    assert captured["url"].startswith("postgresql://")
    assert "connect_args" not in captured["kwargs"]
