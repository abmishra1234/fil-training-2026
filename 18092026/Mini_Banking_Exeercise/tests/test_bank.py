"""Acceptance tests -- Task 6: the Bank orchestrator."""

import json

import pytest

from minibank.accounts import Account, CheckingAccount, SavingsAccount
from minibank.bank import Bank
from minibank.exceptions import (
    AccountClosedError,
    AccountNotFoundError,
    CurrencyMismatchError,
    InsufficientFundsError,
    TransferError,
    UnknownAccountTypeError,
)
from minibank.money import Money
from minibank.transaction import TransactionType


@pytest.fixture
def bank():
    return Bank("FIL Bank")


@pytest.fixture
def populated(bank):
    bank.open_account("SAVINGS", "Asha", Money("10000"))
    bank.open_account("CHECKING", "Ravi", Money("2000"))
    return bank


# --------------------------------------------------------------------- #
# factory
# --------------------------------------------------------------------- #
def test_registry_has_builtin_types():
    assert Bank.ACCOUNT_TYPES["SAVINGS"] is SavingsAccount
    assert Bank.ACCOUNT_TYPES["CHECKING"] is CheckingAccount


def test_open_account_returns_the_right_class(bank):
    assert isinstance(bank.open_account("SAVINGS", "Asha"), SavingsAccount)
    assert isinstance(bank.open_account("CHECKING", "Ravi"), CheckingAccount)


def test_kind_is_case_insensitive(bank):
    assert isinstance(bank.open_account("savings", "Asha"), SavingsAccount)


def test_generated_ids_follow_the_scheme(bank):
    s1 = bank.open_account("SAVINGS", "A")
    s2 = bank.open_account("SAVINGS", "B")
    c1 = bank.open_account("CHECKING", "C")
    assert s1.account_id == "SB0001"
    assert s2.account_id == "SB0002"
    assert c1.account_id == "CH0001"


def test_unknown_kind_raises(bank):
    with pytest.raises(UnknownAccountTypeError) as exc:
        bank.open_account("CRYPTO", "Asha")
    assert exc.value.kind == "CRYPTO"


def test_kwargs_are_forwarded_to_the_concrete_class(bank):
    acct = bank.open_account("CHECKING", "Ravi", overdraft_limit=Money("10000"))
    assert acct.overdraft_limit == Money("10000")


def test_opening_balance_of_wrong_currency_rejected(bank):
    with pytest.raises(CurrencyMismatchError):
        bank.open_account("SAVINGS", "Asha", Money("100", "USD"))


def test_register_new_account_type_without_touching_open_account(bank):
    class ZeroFeeSavings(SavingsAccount):
        @property
        def account_type(self):
            return "ZEROFEE"

    Bank.register_account_type("zerofee", ZeroFeeSavings)
    try:
        acct = bank.open_account("ZEROFEE", "Neha")
        assert isinstance(acct, ZeroFeeSavings)
    finally:
        Bank.ACCOUNT_TYPES.pop("ZEROFEE", None)


def test_register_rejects_non_account():
    with pytest.raises(TypeError):
        Bank.register_account_type("bad", dict)  # type: ignore[arg-type]


# --------------------------------------------------------------------- #
# staticmethod validator
# --------------------------------------------------------------------- #
def test_validate_account_id_accepts_valid_shape():
    assert Bank.validate_account_id("sb0001") == "SB0001"


@pytest.mark.parametrize("bad", ["SB1", "SBB001", "0001SB", "", "SB00001"])
def test_validate_account_id_rejects_bad_shape(bad):
    with pytest.raises(ValueError):
        Bank.validate_account_id(bad)


def test_validator_is_a_staticmethod():
    assert isinstance(Bank.__dict__["validate_account_id"], staticmethod)


# --------------------------------------------------------------------- #
# lookup
# --------------------------------------------------------------------- #
def test_get_account(populated):
    assert populated.get_account("SB0001").owner == "Asha"
    assert populated.get_account("sb0001").owner == "Asha"


def test_get_missing_account_raises(bank):
    with pytest.raises(AccountNotFoundError) as exc:
        bank.get_account("SB9999")
    assert exc.value.account_id == "SB9999"


def test_accounts_snapshot_is_a_tuple(populated):
    assert isinstance(populated.accounts, tuple)
    assert len(populated.accounts) == 2


def test_accounts_of_filters_by_type(populated):
    assert len(populated.accounts_of("savings")) == 1
    assert len(populated.accounts_of("CHECKING")) == 1


def test_close_account_keeps_it_in_the_registry(populated):
    populated.close_account("SB0001")
    assert populated.get_account("SB0001").is_closed
    assert len(populated) == 2


# --------------------------------------------------------------------- #
# total assets
# --------------------------------------------------------------------- #
def test_total_assets_of_empty_bank(bank):
    assert bank.total_assets() == Money.zero("INR")


def test_total_assets_sums_open_accounts(populated):
    assert populated.total_assets() == Money("12000")


def test_total_assets_excludes_closed_accounts(populated):
    populated.close_account("CH0001")
    assert populated.total_assets() == Money("10000")


def test_total_assets_skips_foreign_currency(bank):
    bank.open_account("SAVINGS", "Asha", Money("100"))
    bank.open_account("SAVINGS", "Bob", Money("100", "USD"), currency="USD")
    assert bank.total_assets() == Money("100", "INR")


def test_total_assets_counts_overdrafts_as_negative(bank):
    bank.open_account("SAVINGS", "Asha", Money("10000"))
    chk = bank.open_account("CHECKING", "Ravi")
    chk.withdraw(Money("1000"))
    assert bank.total_assets() == Money("9000")


# --------------------------------------------------------------------- #
# transfer
# --------------------------------------------------------------------- #
def test_transfer_moves_money_both_ways(populated):
    debit, credit = populated.transfer("SB0001", "CH0001", Money("3000"), "rent")
    assert populated.get_account("SB0001").balance == Money("7000")
    assert populated.get_account("CH0001").balance == Money("5000")
    assert debit.type is TransactionType.TRANSFER_OUT
    assert credit.type is TransactionType.TRANSFER_IN
    assert debit.description == credit.description == "rent"


def test_transfer_conserves_total_assets(populated):
    before = populated.total_assets()
    populated.transfer("SB0001", "CH0001", Money("1500"))
    assert populated.total_assets() == before


def test_transfer_to_self_is_refused(populated):
    with pytest.raises(TransferError):
        populated.transfer("SB0001", "SB0001", Money("100"))
    assert len(populated.get_account("SB0001")) == 1


def test_transfer_from_unknown_account(populated):
    with pytest.raises(AccountNotFoundError):
        populated.transfer("SB9999", "CH0001", Money("100"))


def test_transfer_from_closed_account(populated):
    populated.close_account("SB0001")
    with pytest.raises(AccountClosedError):
        populated.transfer("SB0001", "CH0001", Money("100"))


def test_transfer_to_closed_account_leaves_source_untouched(populated):
    populated.close_account("CH0001")
    source = populated.get_account("SB0001")
    before_balance, before_len = source.balance, len(source)
    with pytest.raises(AccountClosedError):
        populated.transfer("SB0001", "CH0001", Money("100"))
    assert source.balance == before_balance
    assert len(source) == before_len


def test_transfer_across_currencies_is_refused(bank):
    bank.open_account("SAVINGS", "Asha", Money("10000"))
    bank.open_account("SAVINGS", "Bob", Money("100", "USD"), currency="USD")
    with pytest.raises(CurrencyMismatchError):
        bank.transfer("SB0001", "SB0002", Money("100"))


def test_underfunded_transfer_records_nothing(populated):
    source = populated.get_account("SB0001")
    dest = populated.get_account("CH0001")
    with pytest.raises(InsufficientFundsError):
        populated.transfer("SB0001", "CH0001", Money("50000"))
    assert source.balance == Money("10000") and len(source) == 1
    assert dest.balance == Money("2000") and len(dest) == 1


def test_transfer_is_atomic_when_the_credit_fails(populated, monkeypatch):
    """If the deposit blows up after the withdrawal, the money comes back."""
    source = populated.get_account("SB0001")
    dest = populated.get_account("CH0001")

    def boom(*args, **kwargs):
        raise AccountClosedError("CH0001")

    monkeypatch.setattr(dest, "transfer_in", boom)

    with pytest.raises(TransferError) as exc:
        populated.transfer("SB0001", "CH0001", Money("1000"))

    assert isinstance(exc.value.__cause__, AccountClosedError)
    assert source.balance == Money("10000"), "debit was not rolled back"


# --------------------------------------------------------------------- #
# month-end processing (duck typing)
# --------------------------------------------------------------------- #
class CountingStrategy:
    """A hand-rolled strategy -- no inheritance from anything."""

    name = "counting"

    def __init__(self):
        self.seen = []

    def apply(self, account):
        self.seen.append(account.account_id)
        return []


def test_monthly_process_accepts_any_duck(populated):
    strategy = CountingStrategy()
    result = populated.monthly_process(strategy)
    assert sorted(strategy.seen) == ["CH0001", "SB0001"]
    assert set(result) == {"SB0001", "CH0001"}
    assert all(v == [] for v in result.values())


def test_monthly_process_rejects_a_non_strategy(populated):
    with pytest.raises(TypeError):
        populated.monthly_process(object())


def test_monthly_process_isolates_failures(populated):
    class Grumpy:
        name = "grumpy"

        def apply(self, account):
            if account.account_type == "SAVINGS":
                raise InsufficientFundsError(Money("1"), Money("0"))
            return []

    result = populated.monthly_process(Grumpy())
    assert result["SB0001"] == []
    assert "CH0001" in result
    assert len(populated.get_account("SB0001").audit_trail) >= 1


# --------------------------------------------------------------------- #
# dunders & serialisation
# --------------------------------------------------------------------- #
def test_len_and_contains_and_getitem(populated):
    assert len(populated) == 2
    assert "SB0001" in populated
    assert "SB9999" not in populated
    assert populated.get_account("SB0001") in populated
    assert populated["SB0001"].owner == "Asha"


def test_iteration_yields_accounts(populated):
    assert all(isinstance(a, Account) for a in populated)
    assert [a.account_id for a in populated] == ["SB0001", "CH0001"]


def test_repr(populated):
    r = repr(populated)
    assert "FIL Bank" in r and "2" in r and "12000.00" in r


def test_to_dict_and_to_json(populated):
    d = populated.to_dict()
    assert set(d) == {"name", "currency", "total_assets", "accounts"}
    assert d["total_assets"] == "12000.00"
    assert len(d["accounts"]) == 2
    assert json.loads(populated.to_json())["name"] == "FIL Bank"
