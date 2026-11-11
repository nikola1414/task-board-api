from fastapi.testclient import TestClient

from tests.conftest import AuthFactory

CREDS = {"email": "Bob@Example.com", "password": "password123"}


def test_register(client: TestClient) -> None:
    r = client.post("/auth/register", json=CREDS)
    assert r.status_code == 201
    assert r.json()["email"] == "bob@example.com"
    assert "password" not in r.text


def test_register_duplicate(client: TestClient) -> None:
    client.post("/auth/register", json=CREDS)
    assert client.post("/auth/register", json=CREDS).status_code == 409


def test_register_validation(client: TestClient) -> None:
    assert client.post("/auth/register", json={"email": "x", "password": "pw"}).status_code == 422


def test_login_ok_and_wrong_password(client: TestClient) -> None:
    client.post("/auth/register", json=CREDS)
    ok = client.post("/auth/login", data={"username": "bob@example.com", "password": "password123"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/auth/login", data={"username": "bob@example.com", "password": "nope"})
    assert bad.status_code == 401


def test_protected_route(client: TestClient, make_user: AuthFactory) -> None:
    assert client.get("/auth/me").status_code == 401
    bad = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401
    r = client.get("/auth/me", headers=make_user())
    assert r.status_code == 200 and r.json()["email"] == "alice@example.com"
