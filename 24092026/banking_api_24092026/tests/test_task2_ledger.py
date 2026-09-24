"""Task 2 - Every money movement writes a Transaction row, atomically."""
import pytest

from app.database import SessionLocal


def _rows(acc_id):
    try:
        from app.models.transaction import Transaction
    except ImportError:
        pytest.fail("Create app/models/transaction.py with a 'Transaction' model (see lab guide Task 2)")
    db = SessionLocal()
    try:
        return db.query(Transaction).filter(Transaction.account_id == acc_id)\
                 .order_by(Transaction.id).all()
    finally:
        db.close()


def test_deposit_and_withdraw_are_recorded(client, make_account):
    acc = make_account("Ledger")
    client.post(f"/api/v1/accounts/{acc}/deposit", json={"amount": 200})
    client.post(f"/api/v1/accounts/{acc}/withdraw", json={"amount": 50})
    rows = _rows(acc)
    assert [r.type for r in rows] == ["DEPOSIT", "WITHDRAWAL"]
    assert [r.amount for r in rows] == [200, 50]
    assert [r.balance_after for r in rows] == [200, 150]
    assert all(r.created_at is not None for r in rows)


def test_transfer_writes_two_legs(client, make_account):
    a, b = make_account("A", balance=300), make_account("B")
    r = client.post("/api/v1/accounts/transfer",
                    json={"from_account_id": a, "to_account_id": b, "amount": 120})
    assert r.status_code == 200
    out, inn = _rows(a)[-1], _rows(b)[-1]
    assert (out.type, out.amount, out.balance_after, out.counterparty_account_id) == ("TRANSFER_OUT", 120, 180, b)
    assert (inn.type, inn.amount, inn.balance_after, inn.counterparty_account_id) == ("TRANSFER_IN", 120, 120, a)


def test_failed_operation_writes_nothing(client, make_account):
    acc = make_account("Broke", balance=10)
    before = len(_rows(acc))
    r = client.post(f"/api/v1/accounts/{acc}/withdraw", json={"amount": 999})
    assert r.status_code == 400
    assert len(_rows(acc)) == before
