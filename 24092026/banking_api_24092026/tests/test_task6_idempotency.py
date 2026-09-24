"""Task 6 (stretch) - Idempotency-Key makes transfer retries safe."""
import uuid


def balance(client, acc):
    return client.get(f"/api/v1/accounts/{acc}").json()["balance"]


def test_retry_with_same_key_moves_money_once(client, make_account):
    a, b = make_account("Payer", balance=1000), make_account("Payee")
    key = str(uuid.uuid4())
    body = {"from_account_id": a, "to_account_id": b, "amount": 250}
    first = client.post("/api/v1/accounts/transfer", json=body, headers={"Idempotency-Key": key})
    retry = client.post("/api/v1/accounts/transfer", json=body, headers={"Idempotency-Key": key})
    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert retry.headers.get("Idempotent-Replayed") == "true"
    assert balance(client, a) == 750 and balance(client, b) == 250


def test_same_key_different_body_is_rejected(client, make_account):
    a, b = make_account("P2", balance=1000), make_account("Q2")
    key = str(uuid.uuid4())
    client.post("/api/v1/accounts/transfer", headers={"Idempotency-Key": key},
                json={"from_account_id": a, "to_account_id": b, "amount": 10})
    r = client.post("/api/v1/accounts/transfer", headers={"Idempotency-Key": key},
                    json={"from_account_id": a, "to_account_id": b, "amount": 99})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "idempotency_key_reused"
    assert balance(client, a) == 990


def test_no_key_keeps_old_behaviour(client, make_account):
    a, b = make_account("P3", balance=100), make_account("Q3")
    body = {"from_account_id": a, "to_account_id": b, "amount": 10}
    client.post("/api/v1/accounts/transfer", json=body)
    client.post("/api/v1/accounts/transfer", json=body)
    assert balance(client, a) == 80        # two calls, two transfers


def test_failed_transfer_is_not_cached(client, make_account):
    a, b = make_account("P4", balance=5), make_account("Q4")
    key = str(uuid.uuid4())
    body = {"from_account_id": a, "to_account_id": b, "amount": 50}
    assert client.post("/api/v1/accounts/transfer", json=body, headers={"Idempotency-Key": key}).status_code == 400
    client.post(f"/api/v1/accounts/{a}/deposit", json={"amount": 100})
    r = client.post("/api/v1/accounts/transfer", json=body, headers={"Idempotency-Key": key})
    assert r.status_code == 200 and balance(client, b) == 50
