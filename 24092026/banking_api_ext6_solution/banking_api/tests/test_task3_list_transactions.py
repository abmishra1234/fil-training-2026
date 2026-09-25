"""Task 3 - Filtering, sorting and pagination on the transaction list."""
import pytest


@pytest.fixture
def busy_account(client, make_account):
    """10 deposits of 10, 20, ..., 100 then withdrawals of 5 and 15."""
    acc = make_account("Busy")
    for amt in range(10, 101, 10):
        client.post(f"/api/v1/accounts/{acc}/deposit", json={"amount": amt})
    client.post(f"/api/v1/accounts/{acc}/withdraw", json={"amount": 5})
    client.post(f"/api/v1/accounts/{acc}/withdraw", json={"amount": 15})
    return acc


def url(acc):
    return f"/api/v1/accounts/{acc}/transactions"


def test_envelope_and_defaults(client, busy_account):
    r = client.get(url(busy_account))
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"items", "page", "limit", "total", "total_pages"}
    assert (body["page"], body["limit"], body["total"], body["total_pages"]) == (1, 25, 12, 1)
    # default sort: newest first
    assert body["items"][0]["type"] == "WITHDRAWAL" and body["items"][0]["amount"] == 15


def test_filter_by_type(client, busy_account):
    body = client.get(url(busy_account), params={"type": "WITHDRAWAL"}).json()
    assert body["total"] == 2
    assert {t["type"] for t in body["items"]} == {"WITHDRAWAL"}


def test_filter_by_amount_range_and_filters_combine_with_and(client, busy_account):
    body = client.get(url(busy_account),
                      params={"type": "DEPOSIT", "min_amount": 30, "max_amount": 60}).json()
    assert sorted(t["amount"] for t in body["items"]) == [30, 40, 50, 60]


def test_sort_by_amount_asc(client, busy_account):
    items = client.get(url(busy_account), params={"sort_by": "amount:asc"}).json()["items"]
    amounts = [t["amount"] for t in items]
    assert amounts == sorted(amounts)


def test_pagination(client, busy_account):
    p = {"sort_by": "amount:asc", "limit": 5}
    page1 = client.get(url(busy_account), params={**p, "page": 1}).json()
    page3 = client.get(url(busy_account), params={**p, "page": 3}).json()
    assert page1["total_pages"] == 3
    assert [t["amount"] for t in page1["items"]] == [5, 10, 15, 20, 30]
    assert [t["amount"] for t in page3["items"]] == [90, 100]
    ids = {t["id"] for t in page1["items"]} & {t["id"] for t in page3["items"]}
    assert not ids, "pages must not overlap"


def test_page_past_the_end_is_empty_not_error(client, busy_account):
    r = client.get(url(busy_account), params={"page": 99})
    assert r.status_code == 200 and r.json()["items"] == []


def test_date_filter_today_includes_everything(client, busy_account):
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    assert client.get(url(busy_account), params={"from_date": today, "to_date": today}).json()["total"] == 12


@pytest.mark.parametrize("params,status", [
    ({"limit": 101}, 422),               # above max
    ({"limit": 0}, 422),
    ({"page": 0}, 422),
    ({"type": "BITCOIN"}, 422),          # not in enum
    ({"sort_by": "owner_name:asc"}, 400),  # not whitelisted
    ({"sort_by": "amount:sideways"}, 400),
    ({"min_amount": 50, "max_amount": 10}, 400),
    ({"from_date": "2030-01-02", "to_date": "2030-01-01"}, 400),
])
def test_bad_query_params_are_rejected(client, busy_account, params, status):
    assert client.get(url(busy_account), params=params).status_code == status


def test_unknown_account_is_404(client):
    assert client.get(url(999999)).status_code == 404


def test_transactions_endpoint_is_v1_only(client, busy_account):
    assert client.get(f"/accounts/{busy_account}/transactions").status_code == 404
