import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPENSE_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_list_get_delete(client):
    r = client.post("/expenses", json={"title": "Lunch", "amount": 250, "category": "food"})
    assert r.status_code == 201
    expense_id = r.json()["id"]

    assert len(client.get("/expenses").json()) == 1
    assert client.get(f"/expenses/{expense_id}").json()["title"] == "Lunch"
    assert client.delete(f"/expenses/{expense_id}").status_code == 204
    assert client.get(f"/expenses/{expense_id}").status_code == 404


def test_filter_and_summary(client):
    client.post("/expenses", json={"title": "Cab", "amount": 300, "category": "travel"})
    client.post("/expenses", json={"title": "Tea", "amount": 20.5, "category": "food"})
    client.post("/expenses", json={"title": "Dinner", "amount": 400, "category": "food"})

    assert [e["title"] for e in client.get("/expenses?category=food").json()] == ["Tea", "Dinner"]
    s = client.get("/expenses/summary").json()
    assert s == {"count": 3, "total": 720.5, "by_category": {"food": 420.5, "travel": 300.0}}


def test_validation(client):
    assert client.post("/expenses", json={"title": "Bad", "amount": -5}).status_code == 422
    assert client.delete("/expenses/999").status_code == 404
