"""Acceptance tests -- Task 4: the account hierarchy."""

import json
from abc import ABC
from decimal import Decimal

import pytest

from minibank.accounts import (
    Account,
    CheckingAccount,
    InterestBearingAccount,
    SavingsAccount,
)
from minibank.exceptions import (
    AccountClosedError,
    CurrencyMismatchError,
    InsufficientFundsError,
    InvalidAmountError,
    OverdraftLimitExceededError,
)
from minibank.mixins import AuditableMixin, JSONSerializableMixin
from minibank.money import Money
from minibank.transaction import TransactionType


@pytest.fixture
def savings():
    return SavingsAccount("SB0001", "Asha", opening_balance=Money("5000"))


@pytest.fixture
def checking():
    return CheckingAccount("CH0001", "Ravi", opening_balance=Money("1000"))


# --------------------------------------------------------------------- #
# structure
# --------------------------------------------------------------------- #
def test_account_is_abstract():
    assert issubclass(Account, ABC)
    with pytest.raises(TypeError):
        Account("SB0001", "Asha")  # type: ignore[abstract]


def test_interest_bearing_is_abstract():
    with pytest.raises(TypeError):
        InterestBearingAccount("SB0001", "Asha")  # type: ignore[abstract]


def test_mro_and_mixins():
    assert issubclass(Account, JSONSerializableMixin)
    assert issubclass(Account, AuditableMixin)
    assert issubclass(SavingsAccount, InterestBearingAccount)
    assert not issubclass(CheckingAccount, InterestBearingAccount)


def test_account_types(savings, checking):
    assert savings.account_type == "SAVINGS"
    assert checking.account_type == "CHECKING"


def test_owner_must_be_non_empty():
    with pytest.raises(ValueError):
        SavingsAccount("SB0001", "   ")


def test_negative_opening_balance_rejected():
    with pytest.raises(InvalidAmountError):
        SavingsAccount("SB0001", "Asha", opening_balance=Money("-1"))


def test_opening_balance_is_recorded_in_ledger(savings):
    assert len(savings) == 1
    assert savings.ledger[0].type is TransactionType.DEPOSIT
    assert savings.balance == Money("5000")


def test_zero_opening_balance_creates_no_transaction():
    acct = SavingsAccount("SB0002", "Asha")
    assert len(acct) == 0
    assert acct.balance == Money.zero()


# --------------------------------------------------------------------- #
# encapsulation
# --------------------------------------------------------------------- #
def test_balance_has_no_setter(savings):
    with pytest.raises(AttributeError):
        savings.balance = Money("1000000")


def test_ledger_snapshot_is_a_tuple_and_cannot_be_mutated(savings):
    assert isinstance(savings.ledger, tuple)
    before = len(savings)
    ledger = savings.ledger
    with pytest.raises(AttributeError):
        ledger.append("hack")  # type: ignore[attr-defined]
    assert len(savings) == before


def test_no_public_balance_attribute(savings):
    public = [n for n in vars(savings) if not n.startswith("_")]
    assert public == [], f"state must be private, found: {public}"


# --------------------------------------------------------------------- #
# deposit
# --------------------------------------------------------------------- #
def test_deposit_increases_balance_and_returns_txn(savings):
    txn = savings.deposit(Money("500"), "salary")
    assert savings.balance == Money("5500")
    assert txn.type is TransactionType.DEPOSIT
    assert txn.balance_after == Money("5500")
    assert txn.description == "salary"
    assert savings.ledger[-1] is txn


@pytest.mark.parametrize("bad", ["0", "-100"])
def test_non_positive_deposit_rejected(savings, bad):
    with pytest.raises(InvalidAmountError):
        savings.deposit(Money(bad))
    assert savings.balance == Money("5000")


def test_deposit_of_wrong_type_rejected(savings):
    with pytest.raises(InvalidAmountError):
        savings.deposit(500)  # type: ignore[arg-type]


def test_deposit_of_wrong_currency_rejected(savings):
    with pytest.raises(CurrencyMismatchError):
        savings.deposit(Money("500", "USD"))


# --------------------------------------------------------------------- #
# withdraw -- savings
# --------------------------------------------------------------------- #
def test_savings_minimum_balance_default(savings):
    assert savings.minimum_balance == Money("1000")
    assert savings.withdrawable_balance == Money("4000")


def test_savings_withdraw_within_limit(savings):
    txn = savings.withdraw(Money("4000"))
    assert savings.balance == Money("1000")
    assert txn.type is TransactionType.WITHDRAWAL


def test_savings_withdraw_breaching_minimum_is_refused(savings):
    with pytest.raises(InsufficientFundsError) as exc:
        savings.withdraw(Money("4500"))
    assert exc.value.requested == Money("4500")
    assert exc.value.available == Money("4000")


def test_failed_withdrawal_changes_nothing(savings):
    before_balance, before_len = savings.balance, len(savings)
    with pytest.raises(InsufficientFundsError):
        savings.withdraw(Money("99999"))
    assert savings.balance == before_balance
    assert len(savings) == before_len


def test_failed_withdrawal_is_audited(savings):
    with pytest.raises(InsufficientFundsError):
        savings.withdraw(Money("99999"))
    assert any("reject" in entry.lower() for entry in savings.audit_trail)


def test_withdrawable_never_negative():
    acct = SavingsAccount("SB0003", "Asha", opening_balance=Money("500"))
    assert acct.withdrawable_balance == Money("0")


def test_custom_minimum_balance():
    acct = SavingsAccount(
        "SB0004", "Asha", opening_balance=Money("5000"), minimum_balance=Money("0")
    )
    acct.withdraw(Money("5000"))
    assert acct.balance == Money("0")


# --------------------------------------------------------------------- #
# withdraw -- checking / overdraft
# --------------------------------------------------------------------- #
def test_checking_overdraft_defaults(checking):
    assert checking.overdraft_limit == Money("5000")
    assert checking.withdrawable_balance == Money("6000")


def test_checking_can_go_overdrawn(checking):
    checking.withdraw(Money("3000"))
    assert checking.balance == Money("-2000")


def test_checking_at_exact_overdraft_limit(checking):
    checking.withdraw(Money("6000"))
    assert checking.balance == Money("-5000")


def test_checking_beyond_limit_raises_overdraft_error(checking):
    with pytest.raises(OverdraftLimitExceededError) as exc:
        checking.withdraw(Money("6000.01"))
    assert exc.value.limit == Money("5000")
    assert checking.balance == Money("1000")


def test_overdraft_error_is_an_insufficient_funds_error(checking):
    with pytest.raises(InsufficientFundsError):
        checking.withdraw(Money("999999"))


def test_savings_does_not_raise_overdraft_error(savings):
    with pytest.raises(InsufficientFundsError) as exc:
        savings.withdraw(Money("999999"))
    assert not isinstance(exc.value, OverdraftLimitExceededError)


# --------------------------------------------------------------------- #
# polymorphism
# --------------------------------------------------------------------- #
def test_same_call_different_behaviour(savings, checking):
    for acct in (savings, checking):
        acct.deposit(Money("100"))
    assert savings.balance == Money("5100")
    assert checking.balance == Money("1100")
    assert savings.withdrawable_balance != checking.withdrawable_balance


def test_withdraw_is_not_overridden_in_subclasses():
    assert "withdraw" not in vars(SavingsAccount)
    assert "withdraw" not in vars(CheckingAccount)


# --------------------------------------------------------------------- #
# interest
# --------------------------------------------------------------------- #
def test_default_interest_rate(savings):
    assert savings.annual_interest_rate == Decimal("0.04")


def test_monthly_interest_maths():
    acct = SavingsAccount(
        "SB0005", "Asha", opening_balance=Money("12000"), interest_rate=Decimal("0.12")
    )
    assert acct.monthly_interest() == Money("120.00")


def test_accrual_appends_interest_transaction():
    acct = SavingsAccount("SB0006", "Asha", opening_balance=Money("12000"),
                          interest_rate=Decimal("0.12"))
    txn = acct.accrue_monthly_interest()
    assert txn is not None
    assert txn.type is TransactionType.INTEREST
    assert acct.balance == Money("12120")


def test_no_interest_on_zero_balance():
    acct = SavingsAccount("SB0007", "Asha", minimum_balance=Money("0"))
    assert acct.monthly_interest() == Money("0")
    assert acct.accrue_monthly_interest() is None
    assert len(acct) == 0


def test_checking_has_no_interest(checking):
    assert not hasattr(checking, "accrue_monthly_interest")


# --------------------------------------------------------------------- #
# fees
# --------------------------------------------------------------------- #
def test_fee_defaults(savings, checking):
    assert savings.monthly_fee() == Money("0")
    assert checking.monthly_fee() == Money("150")


# --------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------- #
def test_close_blocks_money_movement(savings):
    savings.close()
    assert savings.is_closed
    with pytest.raises(AccountClosedError):
        savings.deposit(Money("1"))
    with pytest.raises(AccountClosedError):
        savings.withdraw(Money("1"))


def test_close_is_idempotent(savings):
    savings.close()
    savings.close()
    assert savings.is_closed


# --------------------------------------------------------------------- #
# dunders
# --------------------------------------------------------------------- #
def test_len_counts_transactions(savings):
    savings.deposit(Money("1"))
    savings.deposit(Money("1"))
    assert len(savings) == 3


def test_iteration_yields_transactions(savings):
    savings.deposit(Money("1"))
    assert [t.type for t in savings] == [
        TransactionType.DEPOSIT,
        TransactionType.DEPOSIT,
    ]


def test_repr(savings):
    r = repr(savings)
    assert r.startswith("SavingsAccount(")
    assert "SB0001" in r and "Asha" in r and "5000.00" in r


def test_identity_is_the_account_id():
    a = SavingsAccount("SB0001", "Asha")
    b = CheckingAccount("SB0001", "Someone else")
    c = SavingsAccount("SB0002", "Asha")
    assert a == b and hash(a) == hash(b)
    assert a != c
    assert (a == "SB0001") is False


# --------------------------------------------------------------------- #
# mixins in action
# --------------------------------------------------------------------- #
def test_to_dict_common_keys(savings):
    d = savings.to_dict()
    for key in (
        "account_id",
        "account_type",
        "owner",
        "currency",
        "balance",
        "is_closed",
        "transactions",
    ):
        assert key in d, key
    assert d["balance"] == "5000.00"
    assert d["is_closed"] is False
    assert len(d["transactions"]) == 1


def test_savings_to_dict_extra_keys(savings):
    d = savings.to_dict()
    assert d["minimum_balance"] == "1000.00"
    assert d["interest_rate"] == "0.04"


def test_checking_to_dict_extra_keys(checking):
    d = checking.to_dict()
    assert d["overdraft_limit"] == "5000.00"
    assert d["monthly_fee"] == "150.00"


def test_to_json_is_valid_json(savings):
    parsed = json.loads(savings.to_json())
    assert parsed["account_id"] == "SB0001"


def test_audit_trail_is_read_only_tuple(savings):
    assert isinstance(savings.audit_trail, tuple)
    assert any("open" in e.lower() for e in savings.audit_trail)
    savings.audit("manual note")
    assert "manual note" in savings.audit_trail[-1]
