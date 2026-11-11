import pytest
from fastapi.testclient import TestClient

from tests.conftest import AuthFactory

URL = "/projects/1/tasks"


@pytest.fixture
def users(client: TestClient, make_user: AuthFactory) -> dict[str, dict[str, str]]:
    """alice owns project 1, bob is a viewer, dave is an outsider."""
    u = {n: make_user(f"{n}@example.com") for n in ("alice", "bob", "dave")}
    client.post("/projects", json={"name": "Board"}, headers=u["alice"])
    client.post(
        "/projects/1/members",
        json={"email": "bob@example.com", "role": "viewer"},
        headers=u["alice"],
    )
    return u


def test_crud(client: TestClient, users: dict[str, dict[str, str]]) -> None:
    a = users["alice"]
    r = client.post(URL, json={"title": "Write tests", "assignee_id": 1}, headers=a)
    assert r.status_code == 201
    task = r.json()
    assert task["status"] == "todo" and task["priority"] == "medium"
    assert client.get(f"{URL}/1", headers=users["bob"]).json()["title"] == "Write tests"

    r = client.patch(f"{URL}/1", json={"status": "doing", "assignee_id": None}, headers=a)
    assert r.json()["status"] == "doing" and r.json()["assignee_id"] is None
    # explicit null on a required field is ignored rather than crashing
    assert client.patch(f"{URL}/1", json={"title": None}, headers=a).status_code == 200

    assert client.delete(f"{URL}/1", headers=a).status_code == 204
    assert client.get(f"{URL}/1", headers=a).status_code == 404


def test_assignee_must_be_member(client: TestClient, users: dict[str, dict[str, str]]) -> None:
    r = client.post(URL, json={"title": "x", "assignee_id": 3}, headers=users["alice"])
    assert r.status_code == 400


def test_permissions(client: TestClient, users: dict[str, dict[str, str]]) -> None:
    client.post(URL, json={"title": "t"}, headers=users["alice"])
    assert client.post(URL, json={"title": "x"}, headers=users["bob"]).status_code == 403
    assert client.patch(f"{URL}/1", json={"title": "x"}, headers=users["bob"]).status_code == 403
    assert client.delete(f"{URL}/1", headers=users["bob"]).status_code == 403
    assert client.get(URL, headers=users["dave"]).status_code == 404
    assert client.get(f"{URL}/1", headers=users["dave"]).status_code == 404
    # a task id from another project is a 404, not a leak
    client.post("/projects", json={"name": "Other"}, headers=users["dave"])
    assert client.get("/projects/2/tasks/1", headers=users["dave"]).status_code == 404


def test_list_filters_sort_pagination(client: TestClient, users: dict[str, dict[str, str]]) -> None:
    a = users["alice"]
    for title, prio, status, due in [
        ("alpha", "low", "todo", "2030-01-03"),
        ("beta", "high", "doing", "2030-01-01"),
        ("gamma", "medium", "todo", None),
        ("delta 100%", "high", "done", "2030-01-02"),
    ]:
        body = {"title": title, "priority": prio, "status": status, "due_date": due}
        assert client.post(URL, json=body, headers=a).status_code == 201

    def titles(**params: str | int) -> list[str]:
        r = client.get(URL, params=params, headers=a)
        assert r.status_code == 200, r.text
        return [t["title"] for t in r.json()["items"]]

    assert titles(status="todo", sort="title") == ["alpha", "gamma"]
    assert titles(priority="high", sort="title") == ["beta", "delta 100%"]
    assert titles(sort="-priority")[:2] == ["beta", "delta 100%"]  # enum order, ties by id
    assert titles(sort="due_date") == ["beta", "delta 100%", "alpha", "gamma"]  # nulls last
    assert titles(due_before="2030-01-03", sort="due_date") == ["beta", "delta 100%"]
    assert titles(q="100%") == ["delta 100%"]  # % is escaped, not a wildcard
    assert titles(q="A", sort="title") == ["alpha", "beta", "delta 100%", "gamma"]

    page = client.get(URL, params={"sort": "title", "limit": 2, "offset": 2}, headers=a).json()
    assert page["total"] == 4 and [t["title"] for t in page["items"]] == ["delta 100%", "gamma"]
    assert client.get(URL, params={"limit": 0}, headers=a).status_code == 422
    assert client.get(URL, params={"sort": "password"}, headers=a).status_code == 422


def test_comments(client: TestClient, users: dict[str, dict[str, str]]) -> None:
    client.post(URL, json={"title": "t"}, headers=users["alice"])
    r = client.post(f"{URL}/1/comments", json={"body": "looks good"}, headers=users["alice"])
    assert r.status_code == 201 and r.json()["author_id"] == 1
    assert (
        client.post(f"{URL}/1/comments", json={"body": "x"}, headers=users["bob"]).status_code
        == 403
    )
    assert [c["body"] for c in client.get(f"{URL}/1/comments", headers=users["bob"]).json()] == [
        "looks good"
    ]
    assert client.get(f"{URL}/99/comments", headers=users["alice"]).status_code == 404


def test_activity_log(client: TestClient, users: dict[str, dict[str, str]]) -> None:
    a = users["alice"]
    client.post(URL, json={"title": "t"}, headers=a)
    client.patch(f"{URL}/1", json={"status": "doing", "priority": "medium"}, headers=a)
    client.delete(f"{URL}/1", headers=a)
    log = client.get("/projects/1/activity", headers=users["bob"]).json()
    assert [e["message"] for e in log] == [
        "deleted task 't'",
        "status changed from todo to doing",  # unchanged priority isn't logged
        "created task 't'",
    ]
    assert log[0]["task_id"] is None  # history survives task deletion
