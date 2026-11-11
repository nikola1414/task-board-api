import pytest
from fastapi.testclient import TestClient

from tests.conftest import AuthFactory


@pytest.fixture
def setup(client: TestClient, make_user: AuthFactory) -> dict[str, dict[str, str]]:
    """Project 1 owned by alice; bob is a viewer, carol is a member, dave is an outsider."""
    users = {name: make_user(f"{name}@example.com") for name in ("alice", "bob", "carol", "dave")}
    client.post("/projects", json={"name": "Board"}, headers=users["alice"])
    for name, role in (("bob", "viewer"), ("carol", "member")):
        r = client.post(
            "/projects/1/members",
            json={"email": f"{name}@example.com", "role": role},
            headers=users["alice"],
        )
        assert r.status_code == 201
    return users


def test_create_and_list(client: TestClient, make_user: AuthFactory) -> None:
    h = make_user()
    r = client.post("/projects", json={"name": "P", "description": "d"}, headers=h)
    assert r.status_code == 201 and r.json()["role"] == "owner"
    assert [p["name"] for p in client.get("/projects", headers=h).json()] == ["P"]
    assert client.get("/projects", headers=make_user("other@example.com")).json() == []


def test_get_update_delete(client: TestClient, setup: dict[str, dict[str, str]]) -> None:
    a = setup["alice"]
    assert client.get("/projects/1", headers=setup["bob"]).json()["role"] == "viewer"
    r = client.patch("/projects/1", json={"name": "Renamed"}, headers=a)
    assert r.json()["name"] == "Renamed"
    assert client.delete("/projects/1", headers=a).status_code == 204
    assert client.get("/projects/1", headers=a).status_code == 404


def test_permissions(client: TestClient, setup: dict[str, dict[str, str]]) -> None:
    # outsiders can't even see that the project exists
    assert client.get("/projects/1", headers=setup["dave"]).status_code == 404
    assert client.get("/projects/999", headers=setup["alice"]).status_code == 404
    # non-owners can't modify the project
    assert (
        client.patch("/projects/1", json={"name": "x"}, headers=setup["carol"]).status_code == 403
    )
    assert client.delete("/projects/1", headers=setup["bob"]).status_code == 403
    body = {"email": "dave@example.com"}
    assert client.post("/projects/1/members", json=body, headers=setup["carol"]).status_code == 403


def test_members(client: TestClient, setup: dict[str, dict[str, str]]) -> None:
    a = setup["alice"]
    members = client.get("/projects/1/members", headers=setup["bob"]).json()
    assert [(m["email"], m["role"]) for m in members] == [
        ("alice@example.com", "owner"),
        ("bob@example.com", "viewer"),
        ("carol@example.com", "member"),
    ]
    dup = client.post("/projects/1/members", json={"email": "bob@example.com"}, headers=a)
    assert dup.status_code == 409
    ghost = client.post("/projects/1/members", json={"email": "ghost@example.com"}, headers=a)
    assert ghost.status_code == 404
    assert client.delete("/projects/1/members/2", headers=a).status_code == 204
    assert client.get("/projects/1", headers=setup["bob"]).status_code == 404
    assert client.delete("/projects/1/members/2", headers=a).status_code == 404
    # last owner can't be removed
    assert client.delete("/projects/1/members/1", headers=a).status_code == 409
