"""Task 4 -- the account hierarchy.

    Account (ABC, + JSONSerializableMixin, AuditableMixin)
      |
      +-- InterestBearingAccount (ABC)      adds annual_interest_rate + accrual
      |     |
      |     +-- SavingsAccount              minimum balance, earns interest
      |
      +-- CheckingAccount                   overdraft allowed, monthly fee

ENCAPSULATION RULE (graded)
---------------------------
``_balance`` and ``_ledger`` are private. There is NO public setter. The ONLY
way the balance changes is through ``deposit``, ``withdraw`` or the protected
``_apply`` helper used by subclasses for interest and fees. ``account.balance``
is a read-only property, and ``account.ledger`` returns a ``tuple`` so callers
cannot append to the real list.
"""

from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional

from minibank.exceptions import (
    AccountClosedError,
    CurrencyMismatchError,
    InsufficientFundsError,
    InvalidAmountError,
    OverdraftLimitExceededError,
)
from minibank.mixins import AuditableMixin, JSONSerializableMixin
from minibank.money import DEFAULT_CURRENCY, Money
from minibank.transaction import Transaction, TransactionType


class Account(JSONSerializableMixin, AuditableMixin, ABC):
    """Abstract base for every account type.

    Parameters
    ----------
    account_id:
        Unique, assigned by the :class:`~minibank.bank.Bank` factory.
    owner:
        Non-empty name. Empty/whitespace -> ``ValueError``.
    currency:
        Three-letter code; every Money on this account must match it.
    opening_balance:
        Optional ``Money``. ``None`` means zero. A negative opening balance is
        rejected with ``InvalidAmountError``.

    Class attributes
    ----------------
    _txn_counter:
        A shared ``itertools.count`` used by ``_next_txn_id``. Already provided.
    """

    _txn_counter = itertools.count(1)

    def __init__(
        self,
        account_id: str,
        owner: str,
        currency: str = DEFAULT_CURRENCY,
        opening_balance: Optional[Money] = None,
    ) -> None:
        """Validate, set private state, then ``super().__init__()``.

        Order matters: call ``super().__init__()`` so ``AuditableMixin`` can
        create its log, THEN write your first audit entry
        (``"opened <type> account for <owner>"``).

        If ``opening_balance`` is given and non-zero, record it as a DEPOSIT
        transaction so the ledger explains the balance.
        """
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # read-only surface
    # ------------------------------------------------------------------ #
    @property
    def account_id(self) -> str:
        raise NotImplementedError("TODO")

    @property
    def owner(self) -> str:
        raise NotImplementedError("TODO")

    @property
    def currency(self) -> str:
        raise NotImplementedError("TODO")

    @property
    def balance(self) -> Money:
        """Current balance. READ ONLY -- there must be no setter."""
        raise NotImplementedError("TODO")

    @property
    def ledger(self) -> tuple:
        """Immutable snapshot of the transaction history (a ``tuple``)."""
        raise NotImplementedError("TODO")

    @property
    def is_closed(self) -> bool:
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # abstract contract every subclass must fill in
    # ------------------------------------------------------------------ #
    @property
    @abstractmethod
    def account_type(self) -> str:
        """Short label, e.g. ``"SAVINGS"`` / ``"CHECKING"``. Used in reprs,
        ``to_dict`` and the Bank factory registry."""

    @property
    @abstractmethod
    def withdrawable_balance(self) -> Money:
        """How much can legally be withdrawn RIGHT NOW.

        * Savings : ``balance - minimum_balance`` (never below zero)
        * Checking: ``balance + overdraft_limit``

        ``withdraw`` is written ONCE in the base class in terms of this
        property -- that is the polymorphism the exercise is testing. Do not
        override ``withdraw`` in the subclasses.
        """

    @abstractmethod
    def _insufficient_funds_error(self, requested: Money) -> InsufficientFundsError:
        """Build the right exception for a rejected withdrawal.

        Savings returns ``InsufficientFundsError``; Checking returns
        ``OverdraftLimitExceededError``. Called by the base ``withdraw``.
        """

    # ------------------------------------------------------------------ #
    # money movement
    # ------------------------------------------------------------------ #
    def _next_txn_id(self) -> str:
        """Return ``"T000001"``-style ids from ``Account._txn_counter``."""
        raise NotImplementedError("TODO")

    def _validate(self, amount: Money) -> None:
        """Shared guard for every money movement.

        Raise, in this order:
          1. ``AccountClosedError`` if the account is closed.
          2. ``InvalidAmountError`` if ``amount`` is not a ``Money``.
          3. ``CurrencyMismatchError`` if the currency differs.
          4. ``InvalidAmountError`` if the amount is not strictly positive.
        """
        raise NotImplementedError("TODO")

    def _apply(
        self,
        txn_type: TransactionType,
        amount: Money,
        description: str = "",
    ) -> Transaction:
        """Mutate the balance and append a ledger entry. PROTECTED.

        Credits (``txn_type.is_credit``) add, debits subtract. Returns the
        created ``Transaction``. This is the single place ``_balance`` is
        written -- every other method goes through here.
        """
        raise NotImplementedError("TODO")

    def deposit(self, amount: Money, description: str = "") -> Transaction:
        """Add money. Returns the ledger entry.

        Raises ``AccountClosedError``, ``InvalidAmountError`` (non-positive or
        wrong type) or ``CurrencyMismatchError`` -- see ``_validate``.
        """
        raise NotImplementedError("TODO")

    def withdraw(self, amount: Money, description: str = "") -> Transaction:
        """Remove money. Returns the ledger entry.

        Validate, then compare ``amount`` against ``withdrawable_balance``.
        If it does not fit: write an audit entry describing the rejection and
        raise ``self._insufficient_funds_error(amount)``. Nothing about the
        balance or ledger may change on a failed withdrawal.
        """
        raise NotImplementedError("TODO")

    def transfer_out(self, amount: Money, description: str = "") -> Transaction:
        """Debit leg of a transfer -- same rules as ``withdraw`` but the ledger
        entry is a ``TRANSFER_OUT``.

        Share the guard and the limit check with ``withdraw`` (extract a small
        private helper); copy-pasting the body costs marks.
        """
        raise NotImplementedError("TODO")

    def transfer_in(self, amount: Money, description: str = "") -> Transaction:
        """Credit leg of a transfer -- same rules as ``deposit`` but the ledger
        entry is a ``TRANSFER_IN``."""
        raise NotImplementedError("TODO")

    def close(self) -> None:
        """Mark the account closed.

        Idempotent: closing twice is fine and raises nothing. A non-zero
        balance is allowed to remain (the Bank decides policy). Write an audit
        entry.
        """
        raise NotImplementedError("TODO")

    def monthly_fee(self) -> Money:
        """Fee charged at month end. Default: zero of this currency.
        Override in ``CheckingAccount``."""
        raise NotImplementedError("TODO")

    def statement(self) -> str:
        """Multi-line human statement. Exact layout is up to you; it must
        include the account id, the owner and one line per transaction."""
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # dunders -- MANDATORY
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        """Number of transactions in the ledger, so ``len(account)`` works."""
        raise NotImplementedError("TODO")

    def __repr__(self) -> str:
        """e.g. ``SavingsAccount(id='SB0001', owner='Asha', balance=INR 5000.00)``.
        Use ``type(self).__name__`` so subclasses need no override."""
        raise NotImplementedError("TODO")

    def __eq__(self, other: object) -> bool:
        """Identity is the ``account_id``. Non-Account -> ``NotImplemented``."""
        raise NotImplementedError("TODO")

    def __hash__(self) -> int:
        raise NotImplementedError("TODO")

    def __iter__(self):
        """Iterate over the ledger, so ``for txn in account`` works."""
        raise NotImplementedError("TODO")

    def to_dict(self) -> Dict[str, Any]:
        """Override of the mixin hook. Required exact keys::

            {"account_id": str, "account_type": str, "owner": str,
             "currency": str, "balance": str, "is_closed": bool,
             "transactions": [ {..transaction dicts..} ]}
        """
        raise NotImplementedError("TODO")


class InterestBearingAccount(Account, ABC):
    """Abstract mid-layer for accounts that earn interest.

    Exists to prove you can put an abstract class BETWEEN two concrete levels
    rather than pushing interest onto every account.
    """

    @property
    @abstractmethod
    def annual_interest_rate(self) -> Decimal:
        """Annual rate as a fraction, e.g. ``Decimal("0.04")`` for 4%."""

    def monthly_interest(self) -> Money:
        """Interest for one month: ``balance * annual_interest_rate / 12``.

        Return ``Money.zero(currency)`` when the balance is not positive --
        never pay interest on an overdrawn account.
        Rounding is whatever ``Money`` already does (ROUND_HALF_UP, 2dp).
        """
        raise NotImplementedError("TODO")

    def accrue_monthly_interest(self) -> Optional[Transaction]:
        """Credit one month of interest.

        Return the ``INTEREST`` transaction, or ``None`` when the interest
        works out to zero (no zero-value ledger noise) or the account is
        closed.
        """
        raise NotImplementedError("TODO")


class SavingsAccount(InterestBearingAccount):
    """Interest-earning account that must keep a minimum balance.

    Extra parameters
    ----------------
    minimum_balance:
        Defaults to ``Money("1000", currency)``. Withdrawals may not take the
        balance below it.
    interest_rate:
        Defaults to ``DEFAULT_RATE`` (4% a year).
    """

    DEFAULT_MINIMUM = Decimal("1000.00")
    DEFAULT_RATE = Decimal("0.04")

    def __init__(
        self,
        account_id: str,
        owner: str,
        currency: str = DEFAULT_CURRENCY,
        opening_balance: Optional[Money] = None,
        minimum_balance: Optional[Money] = None,
        interest_rate: Optional[Decimal] = None,
    ) -> None:
        """Set the savings-specific fields, then delegate to ``super().__init__``.

        A negative ``minimum_balance`` or ``interest_rate`` ->
        ``InvalidAmountError``.
        """
        raise NotImplementedError("TODO")

    @property
    def account_type(self) -> str:
        """Return ``"SAVINGS"``."""
        raise NotImplementedError("TODO")

    @property
    def minimum_balance(self) -> Money:
        raise NotImplementedError("TODO")

    @property
    def annual_interest_rate(self) -> Decimal:
        raise NotImplementedError("TODO")

    @property
    def withdrawable_balance(self) -> Money:
        """``balance - minimum_balance``, floored at zero."""
        raise NotImplementedError("TODO")

    def _insufficient_funds_error(self, requested: Money) -> InsufficientFundsError:
        raise NotImplementedError("TODO")

    def to_dict(self) -> Dict[str, Any]:
        """Base dict PLUS ``"minimum_balance"`` (str) and
        ``"interest_rate"`` (str). Call ``super().to_dict()`` -- do not
        re-build the common keys."""
        raise NotImplementedError("TODO")


class CheckingAccount(Account):
    """Everyday account that may go overdrawn up to a limit.

    Extra parameters
    ----------------
    overdraft_limit:
        Defaults to ``Money("5000", currency)``. Must not be negative.
    fee:
        Month-end maintenance fee, defaults to ``Money("150", currency)``.
    """

    DEFAULT_OVERDRAFT = Decimal("5000.00")
    DEFAULT_FEE = Decimal("150.00")

    def __init__(
        self,
        account_id: str,
        owner: str,
        currency: str = DEFAULT_CURRENCY,
        opening_balance: Optional[Money] = None,
        overdraft_limit: Optional[Money] = None,
        fee: Optional[Money] = None,
    ) -> None:
        raise NotImplementedError("TODO")

    @property
    def account_type(self) -> str:
        """Return ``"CHECKING"``."""
        raise NotImplementedError("TODO")

    @property
    def overdraft_limit(self) -> Money:
        raise NotImplementedError("TODO")

    @property
    def withdrawable_balance(self) -> Money:
        """``balance + overdraft_limit``."""
        raise NotImplementedError("TODO")

    def _insufficient_funds_error(self, requested: Money) -> InsufficientFundsError:
        """Return an ``OverdraftLimitExceededError`` carrying the limit."""
        raise NotImplementedError("TODO")

    def monthly_fee(self) -> Money:
        """Override: the configured fee."""
        raise NotImplementedError("TODO")

    def to_dict(self) -> Dict[str, Any]:
        """Base dict PLUS ``"overdraft_limit"`` and ``"monthly_fee"`` (both str)."""
        raise NotImplementedError("TODO")
