"""Ext 6 - Task 5: object-level authorization (OWASP API1 - BOLA)."""
from datetime import date, timedelta


def test_new_account_belongs_to_creator(client, anon_client, login):
    asha = login("asha")
    acc = anon_client.post("/api/v1/accounts/", json={"owner_name": "Asha"}, headers=asha).json()["id"]
    assert anon_client.get(f"/api/v1/accounts/{acc}", headers=asha).status_code == 200


def test_list_shows_only_my_accounts(anon_client, login):
    ravi, meera = login("ravi"), login("meera")
    mine = anon_client.post("/api/v1/accounts/", json={"owner_name": "Ravi"}, headers=ravi).json()["id"]
    anon_client.post("/api/v1/accounts/", json={"owner_name": "Meera"}, headers=meera)
    ids = [a["id"] for a in anon_client.get("/api/v1/accounts/", headers=ravi).json()]
    assert ids == [mine]


def test_cannot_read_someone_elses_account(anon_client, login, make_account):
    victim = make_account("Victim", balance=5000)        # owned by the default customer
    attacker = login("attacker1")
    r = anon_client.get(f"/api/v1/accounts/{victim}", headers=attacker)
    assert r.status_code == 404                          # hide that it even exists
    assert r.json()["error"]["code"] == "account_not_found"


def test_cannot_withdraw_or_deposit_on_someone_elses_account(client, anon_client, login, make_account):
    victim = make_account("Victim2", balance=5000)
    attacker = login("attacker2")
    for op in ("withdraw", "deposit"):
        r = anon_client.post(f"/api/v1/accounts/{victim}/{op}", json={"amount": 100}, headers=attacker)
        assert r.status_code == 404
    assert client.get(f"/api/v1/accounts/{victim}").json()["balance"] == 5000


def test_cannot_transfer_from_someone_elses_account(client, anon_client, login, make_account):
    victim = make_account("Victim3", balance=5000)
    attacker = login("attacker3")
    mine = make_account("Attacker", headers=attacker)
    r = anon_client.post("/api/v1/accounts/transfer", headers=attacker,
                         json={"from_account_id": victim, "to_account_id": mine, "amount": 4999})
    assert r.status_code == 404
    assert client.get(f"/api/v1/accounts/{victim}").json()["balance"] == 5000


def test_can_transfer_to_someone_elses_account(client, anon_client, login, make_account):
    payee = make_account("Payee")                         # default customer's account
    sender = login("sender1")
    mine = make_account("Sender", balance=300, headers=sender)
    r = anon_client.post("/api/v1/accounts/transfer", headers=sender,
                         json={"from_account_id": mine, "to_account_id": payee, "amount": 100})
    assert r.status_code == 200
    assert client.get(f"/api/v1/accounts/{payee}").json()["balance"] == 100


def test_cannot_read_someone_elses_transactions(anon_client, login, make_account):
    victim = make_account("Victim4", balance=10)
    r = anon_client.get(f"/api/v1/accounts/{victim}/transactions", headers=login("attacker4"))
    assert r.status_code == 404


def test_cannot_touch_someone_elses_scheduled_payment(client, anon_client, login, make_account):
    acc = make_account("Payer", balance=1000, kyc=True)
    pid = client.post(f"/api/v1/accounts/{acc}/scheduled-payments", json={
        "payee_name": "Landlord", "payee_account": "IN00LANDLORD01", "amount": 250,
        "frequency": "MONTHLY", "next_run_date": str(date.today() + timedelta(days=5))}).json()["id"]
    attacker = login("attacker5")
    assert anon_client.get(f"/api/v1/scheduled-payments/{pid}", headers=attacker).status_code == 404
    assert anon_client.patch(f"/api/v1/scheduled-payments/{pid}", json={"amount": 1},
                             headers=attacker).status_code == 404
    assert anon_client.delete(f"/api/v1/scheduled-payments/{pid}", headers=attacker).status_code == 404
    assert client.get(f"/api/v1/scheduled-payments/{pid}").json()["amount"] == 250


def test_idempotency_keys_are_scoped_per_user(anon_client, login, make_account):
    u1, u2 = login("idem.one"), login("idem.two")
    a1, b1 = make_account("A1", balance=100, headers=u1), make_account("B1", headers=u1)
    a2, b2 = make_account("A2", balance=100, headers=u2), make_account("B2", headers=u2)
    key = {"Idempotency-Key": "same-key-123"}
    r1 = anon_client.post("/api/v1/accounts/transfer", headers={**u1, **key},
                          json={"from_account_id": a1, "to_account_id": b1, "amount": 10})
    r2 = anon_client.post("/api/v1/accounts/transfer", headers={**u2, **key},
                          json={"from_account_id": a2, "to_account_id": b2, "amount": 20})
    assert r1.status_code == r2.status_code == 200
    assert "Idempotent-Replayed" not in r2.headers              # NOT user 1's cached response
    assert r2.json()["from_account"]["id"] == a2
