import pytest
import redis
from fastapi.testclient import TestClient

from app import cache
from app.config import LOGIN_RATE_LIMIT
from app.db import SessionLocal
from app.models import Task
from tests.conftest import AuthFactory

URL = "/projects/1/tasks"


def test_task_list_cached_and_invalidated(client: TestClient, make_user: AuthFactory) -> None:
    h = make_user()
    client.post("/projects", json={"name": "P"}, headers=h)
    client.post(URL, json={"title": "one"}, headers=h)
    assert client.get(URL, headers=h).json()["total"] == 1

    # A row written behind the API's back is invisible until the cache is invalidated
    with SessionLocal() as db:
        db.add(Task(project_id=1, title="sneaky"))
        db.commit()
    assert client.get(URL, headers=h).json()["total"] == 1

    client.post(URL, json={"title": "three"}, headers=h)  # any write bumps the version
    assert client.get(URL, headers=h).json()["total"] == 3


def test_cache_fails_open(
    client: TestClient, make_user: AuthFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = make_user()
    client.post("/projects", json={"name": "P"}, headers=h)
    monkeypatch.setattr(cache, "client", redis.Redis(port=1, socket_connect_timeout=0.1))
    assert client.post(URL, json={"title": "t"}, headers=h).status_code == 201
    assert client.get(URL, headers=h).json()["total"] == 1
    r = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "password123"}
    )
    assert r.status_code == 200
    assert client.get("/health").status_code == 503


def test_login_rate_limit(client: TestClient) -> None:
    creds = {"username": "nobody@example.com", "password": "wrong-password"}
    codes = [
        client.post("/auth/login", data=creds).status_code for _ in range(LOGIN_RATE_LIMIT + 1)
    ]
    assert codes[:-1] == [401] * LOGIN_RATE_LIMIT
    assert codes[-1] == 429


def test_error_shape_and_request_id(client: TestClient, make_user: AuthFactory) -> None:
    r = client.get("/projects/42", headers={**make_user(), "X-Request-ID": "abc-123"})
    assert r.status_code == 404
    assert r.headers["X-Request-ID"] == "abc-123"
    assert r.json() == {
        "error": {"status": 404, "message": "Project not found"},
        "request_id": "abc-123",
    }
    bad = client.post("/auth/register", json={"email": "nope"}, headers={"X-Request-ID": "bad id!"})
    assert bad.status_code == 422
    assert bad.headers["X-Request-ID"] != "bad id!"  # unsafe ids are replaced
    fields = {d["field"] for d in bad.json()["error"]["message"]}
    assert fields == {"body.email", "body.password"}


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "postgres": "ok", "redis": "ok"}
