from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.dependencies import get_db
from app.database.database import Base
from app.main import app
from app.services import file_service


@pytest.fixture(autouse=True)
def test_stripe_config(monkeypatch) -> None:
    monkeypatch.setattr("app.services.stripe_service.STRIPE_KEY", "sk_test_dummy")
    monkeypatch.setattr("app.services.stripe_service.STRIPE_WEBHOOK_SECRET", "")


@pytest.fixture(autouse=True)
def product_images_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(file_service, "PRODUCT_IMAGES_DIR", tmp_path / "product-images")


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    app.state.limiter.enabled = False

    with TestClient(app) as test_client:
        yield test_client

    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": "admin@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 201, f"Registration failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
