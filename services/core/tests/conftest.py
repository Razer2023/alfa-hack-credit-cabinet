import os
import tempfile
from pathlib import Path

# Настройки задаются до импорта приложения: тесты работают на отдельной SQLite без фонового обработчика
_DB = Path(tempfile.mkdtemp()) / "test.db"
os.environ.update(
    CORE_DATABASE_URL=f"sqlite:///{_DB.as_posix()}",
    CORE_WORKER_ENABLED="false",
    CORE_DEMO_PASSWORD="test-pass",
    CORE_JWT_SECRET="test-secret-0123456789abcdef0123456789",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.pipeline import process_once  # noqa: E402
from app.seed import seed  # noqa: E402

INN = {"coffee": "7701234567", "stroy": "7702345678", "vector": "7703456789"}


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)
    yield


@pytest.fixture
def api():
    with TestClient(app) as client:
        yield client


class User:
    """Тестовый пользователь: обёртка над API с его токеном."""

    def __init__(self, api: TestClient, login: str):
        self.api = api
        self.login = login
        response = api.post("/api/v1/auth/login", json={"login": login, "password": "test-pass"})
        assert response.status_code == 200, response.text
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    def get(self, path: str, **kwargs):
        return self.api.get(f"/api/v1{path}", headers=self.headers, **kwargs)

    def post(self, path: str, json: dict | None = None):
        return self.api.post(f"/api/v1{path}", headers=self.headers, json=json or {})

    def patch(self, path: str, json: dict):
        return self.api.patch(f"/api/v1{path}", headers=self.headers, json=json)


@pytest.fixture
def login(api):
    return lambda name: User(api, name)


def run_pipeline() -> None:
    """Прогоняет фоновый обработчик, пока заявки не остановятся в ожидании людей."""
    for _ in range(20):
        if process_once() == 0:
            return
    raise AssertionError("Конвейер не остановился")


def submit(client: User, product: str, amount: int, term: int, purpose: str = "Закупка товара") -> dict:
    """Клиент создаёт заявку, заполняет её по ИНН и отправляет с кодом."""
    app = client.post("/applications", {"product_code": product}).json()
    path = f"/applications/{app['id']}"
    assert client.patch(path, {"amount": amount, "term_months": term, "purpose": purpose}).status_code == 200
    assert client.post(f"{path}/prefill", {"inn": INN[client.login]}).status_code == 200
    code = client.post(f"{path}/submit/code").json()
    response = client.post(
        f"{path}/submit/confirm", {"confirmation_id": code["confirmation_id"], "code": code["demo_code"]}
    )
    assert response.status_code == 200, response.text
    return response.json()


def sign(client: User, app_id: str) -> dict:
    path = f"/applications/{app_id}"
    code = client.post(f"{path}/sign/code").json()
    response = client.post(f"{path}/sign/confirm", {"confirmation_id": code["confirmation_id"], "code": code["demo_code"]})
    assert response.status_code == 200, response.text
    return response.json()
