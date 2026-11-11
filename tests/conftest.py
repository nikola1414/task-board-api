import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://taskboard:taskboard@localhost:5432/taskboard_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

from collections.abc import Callable, Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

AuthFactory = Callable[..., dict[str, str]]


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_db() -> Iterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def make_user(client: TestClient) -> AuthFactory:
    """Register + log in a user, return auth headers."""

    def _make(email: str = "alice@example.com") -> dict[str, str]:
        client.post("/auth/register", json={"email": email, "password": "password123"})
        r = client.post("/auth/login", data={"username": email, "password": "password123"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make
