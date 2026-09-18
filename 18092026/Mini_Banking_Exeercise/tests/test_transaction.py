"""Acceptance tests -- Task 2: Transaction."""

from datetime import datetime, timezone

import pytest

from minibank.exceptions import InvalidAmountError
from minibank.money import Money
from minibank.transaction import Transaction, TransactionType


def make(txn_id="T1", kind=TransactionType.DEPOSIT, amount="100", after="100"):
    return Transaction(txn_id, kind, Money(amount), Money(after), "test")


def test_fields_are_stored():
    t = make()
    assert t.txn_id == "T1"
    assert t.type is TransactionType.DEPOSIT
    assert t.amount == Money("100")
    assert t.balance_after == Money("100")
    assert t.description == "test"


def test_timestamp_defaults_to_aware_utc():
    t = make()
    assert isinstance(t.timestamp, datetime)
    assert t.timestamp.tzinfo is not None


def test_is_immutable():
    t = make()
    with pytest.raises(Exception):
        t.amount = Money("1")


def test_negative_amount_rejected():
    with pytest.raises(InvalidAmountError):
        Transaction("T1", TransactionType.DEPOSIT, Money("-1"), Money("0"))


def test_non_money_amount_rejected():
    with pytest.raises(InvalidAmountError):
        Transaction("T1", TransactionType.DEPOSIT, 100, Money("0"))


def test_non_enum_type_rejected():
    with pytest.raises(InvalidAmountError):
        Transaction("T1", "DEPOSIT", Money("1"), Money("1"))


@pytest.mark.parametrize(
    "kind, credit",
    [
        (TransactionType.DEPOSIT, True),
        (TransactionType.TRANSFER_IN, True),
        (TransactionType.INTEREST, True),
        (TransactionType.WITHDRAWAL, False),
        (TransactionType.TRANSFER_OUT, False),
        (TransactionType.FEE, False),
    ],
)
def test_is_credit_flags(kind, credit):
    assert kind.is_credit is credit


def test_signed_amount_follows_direction():
    assert make(kind=TransactionType.DEPOSIT).signed_amount == Money("100")
    assert make(kind=TransactionType.FEE).signed_amount == Money("-100")


def test_hash_and_equality_use_txn_id():
    a = make("T1", amount="100")
    b = make("T1", amount="999")
    c = make("T2")
    assert a == b and hash(a) == hash(b)
    assert a != c
    assert len({a, b, c}) == 2


def test_equality_with_other_type():
    assert (make() == "T1") is False


def test_repr_mentions_id_type_and_amount():
    r = repr(make())
    assert "T1" in r and "DEPOSIT" in r and "100.00" in r


def test_to_dict_shape():
    t = make()
    d = t.to_dict()
    assert set(d) == {
        "txn_id",
        "type",
        "amount",
        "currency",
        "balance_after",
        "description",
        "timestamp",
    }
    assert d["type"] == "DEPOSIT"
    assert d["amount"] == "100.00"
    assert d["currency"] == "INR"
    assert d["balance_after"] == "100.00"
    assert d["timestamp"] == t.timestamp.isoformat()
