"""Acceptance tests -- Task 5: month-end strategies."""

from decimal import Decimal

import pytest

from minibank.bank import Bank
from minibank.money import Money
from minibank.strategies import (
    CompositeStrategy,
    InterestStrategy,
    MaintenanceFeeStrategy,
)
from minibank.transaction import TransactionType


@pytest.fixture
def bank():
    b = Bank("FIL Bank")
    b.open_account("SAVINGS", "Asha", Money("12000"), interest_rate=Decimal("0.12"))
    b.open_account("CHECKING", "Ravi", Money("2000"))
    return b


# --------------------------------------------------------------------- #
# interest
# --------------------------------------------------------------------- #
def test_interest_strategy_credits_only_savings(bank):
    result = bank.monthly_process(InterestStrategy())
    assert len(result["SB0001"]) == 1
    assert result["SB0001"][0].type is TransactionType.INTEREST
    assert result["CH0001"] == []
    assert bank.get_account("SB0001").balance == Money("12120")
    assert bank.get_account("CH0001").balance == Money("2000")


def test_interest_strategy_skips_closed_accounts(bank):
    bank.close_account("SB0001")
    assert bank.monthly_process(InterestStrategy())["SB0001"] == []


def test_strategy_has_a_name():
    assert InterestStrategy().name == "interest"
    assert MaintenanceFeeStrategy().name == "maintenance-fee"


# --------------------------------------------------------------------- #
# fees
# --------------------------------------------------------------------- #
def test_fee_strategy_charges_checking_only(bank):
    result = bank.monthly_process(MaintenanceFeeStrategy())
    assert len(result["CH0001"]) == 1
    assert result["CH0001"][0].type is TransactionType.WITHDRAWAL
    assert bank.get_account("CH0001").balance == Money("1850")
    assert result["SB0001"] == []          # savings fee is zero -> no entry
    assert bank.get_account("SB0001").balance == Money("12000")


def test_fee_strategy_swallows_only_insufficient_funds():
    b = Bank("FIL Bank")
    acct = b.open_account("CHECKING", "Broke", overdraft_limit=Money("0"))
    result = b.monthly_process(MaintenanceFeeStrategy())
    assert result["CH0001"] == []
    assert acct.balance == Money("0")
    assert any("fee" in e.lower() for e in acct.audit_trail)


def test_fee_goes_through_withdraw_so_limits_apply():
    b = Bank("FIL Bank")
    acct = b.open_account("CHECKING", "Ravi", Money("100"), overdraft_limit=Money("40"))
    b.monthly_process(MaintenanceFeeStrategy())
    assert acct.balance == Money("100"), "a 150 fee must not breach a 140 limit"


# --------------------------------------------------------------------- #
# composition
# --------------------------------------------------------------------- #
def test_composite_runs_children_in_order(bank):
    month_end = CompositeStrategy(InterestStrategy(), MaintenanceFeeStrategy())
    result = bank.monthly_process(month_end)
    assert len(result["SB0001"]) == 1                  # interest only
    assert len(result["CH0001"]) == 1                  # fee only
    assert bank.get_account("SB0001").balance == Money("12120")
    assert bank.get_account("CH0001").balance == Money("1850")


def test_composite_name():
    month_end = CompositeStrategy(InterestStrategy(), MaintenanceFeeStrategy())
    assert month_end.name == "interest+maintenance-fee"


def test_composite_rejects_a_non_strategy():
    with pytest.raises(TypeError):
        CompositeStrategy(InterestStrategy(), "not a strategy")


def test_composite_nests():
    inner = CompositeStrategy(InterestStrategy())
    outer = CompositeStrategy(inner, MaintenanceFeeStrategy())
    assert outer.name == "interest+maintenance-fee"
