"""Task 4 - Scheduled payments: correct verbs and status codes."""
from datetime import date, timedelta

import pytest

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def payload(**over):
    body = {"payee_name": "Landlord", "payee_account": "HDFC0001234",
            "amount": 25000, "frequency": "MONTHLY", "next_run_date": TOMORROW}
    body.update(over)
    return body


@pytest.fixture
def kyc_account(make_account):
    return make_account("Payer", kyc=True)


def test_create_returns_201_and_location(client, kyc_account):
    r = client.post(f"/api/v1/accounts/{kyc_account}/scheduled-payments", json=payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "ACTIVE" and body["account_id"] == kyc_account
    assert r.headers["Location"] == f"/api/v1/scheduled-payments/{body['id']}"


def test_list_and_get(client, kyc_account):
    pid = client.post(f"/api/v1/accounts/{kyc_account}/scheduled-payments", json=payload()).json()["id"]
    lst = client.get(f"/api/v1/accounts/{kyc_account}/scheduled-payments")
    assert lst.status_code == 200 and pid in [p["id"] for p in lst.json()]
    assert client.get(f"/api/v1/scheduled-payments/{pid}").json()["payee_name"] == "Landlord"


def test_patch_changes_only_sent_fields(client, kyc_account):
    pid = client.post(f"/api/v1/accounts/{kyc_account}/scheduled-payments", json=payload()).json()["id"]
    r = client.patch(f"/api/v1/scheduled-payments/{pid}", json={"status": "PAUSED"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "PAUSED"
    assert body["amount"] == 25000 and body["payee_name"] == "Landlord"   # untouched


def test_list_can_filter_by_status(client, make_account):
    acc = make_account("Filter", kyc=True)
    a = client.post(f"/api/v1/accounts/{acc}/scheduled-payments", json=payload()).json()["id"]
    client.post(f"/api/v1/accounts/{acc}/scheduled-payments", json=payload(payee_name="Gym"))
    client.patch(f"/api/v1/scheduled-payments/{a}", json={"status": "PAUSED"})
    paused = client.get(f"/api/v1/accounts/{acc}/scheduled-payments", params={"status": "PAUSED"}).json()
    assert [p["id"] for p in paused] == [a]


def test_delete_is_204_then_404(client, kyc_account):
    pid = client.post(f"/api/v1/accounts/{kyc_account}/scheduled-payments", json=payload()).json()["id"]
    r = client.delete(f"/api/v1/scheduled-payments/{pid}")
    assert r.status_code == 204 and r.content == b""
    assert client.delete(f"/api/v1/scheduled-payments/{pid}").status_code == 404
    assert client.get(f"/api/v1/scheduled-payments/{pid}").status_code == 404


@pytest.mark.parametrize("override,status", [
    ({"amount": 0}, 422),
    ({"amount": -5}, 422),
    ({"frequency": "DAILY"}, 422),
    ({"next_run_date": YESTERDAY}, 400),
])
def test_create_validation(client, kyc_account, override, status):
    r = client.post(f"/api/v1/accounts/{kyc_account}/scheduled-payments", json=payload(**override))
    assert r.status_code == status, r.text


def test_create_requires_kyc(client, make_account):
    acc = make_account("No KYC", kyc=False)
    r = client.post(f"/api/v1/accounts/{acc}/scheduled-payments", json=payload())
    assert r.status_code == 403


def test_create_for_unknown_account_is_404(client):
    assert client.post("/api/v1/accounts/999999/scheduled-payments", json=payload()).status_code == 404


def test_patch_with_empty_body_is_400(client, kyc_account):
    pid = client.post(f"/api/v1/accounts/{kyc_account}/scheduled-payments", json=payload()).json()["id"]
    assert client.patch(f"/api/v1/scheduled-payments/{pid}", json={}).status_code == 400


def test_wrong_verb_is_405(client, kyc_account):
    pid = client.post(f"/api/v1/accounts/{kyc_account}/scheduled-payments", json=payload()).json()["id"]
    assert client.post(f"/api/v1/scheduled-payments/{pid}", json=payload()).status_code == 405
