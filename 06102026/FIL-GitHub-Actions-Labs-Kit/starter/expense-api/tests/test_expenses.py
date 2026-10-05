"""API 2: GET /api/v1/expenses + security headers"""
from tests.conftest import ASHA, PRIYA

URL = "/api/v1/expenses"


def test_list_requires_token(client):
    assert client.get(URL).status_code == 401


def test_employee_sees_only_own_expenses(client, login):
    r = client.get(URL, headers=login(ASHA))
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "asha should have at least one expense in the seed"
    assert {e["employee_id"] for e in items} == {1}


def test_manager_sees_team_expenses(client, login):
    r = client.get(URL, headers=login(PRIYA), params={"page_size": 100})
    assert r.status_code == 200
    assert len({e["employee_id"] for e in r.json()["items"]}) > 1


def test_security_headers_present(client):
    r = client.get(URL)
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
