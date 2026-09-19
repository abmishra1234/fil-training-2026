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
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("owner must be non-empty")

        zero = Money.zero(currency)
        if opening_balance is not None:
            if not isinstance(opening_balance, Money):
                raise InvalidAmountError(opening_balance, "opening balance must be Money")
            if opening_balance.currency != zero.currency:
                raise CurrencyMismatchError(zero.currency, opening_balance.currency)
            if opening_balance.is_negative:
                raise InvalidAmountError(opening_balance, "opening balance cannot be negative")

        self._account_id = account_id
        self._owner = owner.strip()
        self._currency = zero.currency
        self._balance = zero
        self._ledger: List[Transaction] = []
        self._is_closed = False
        super().__init__()
        self.audit(f"opened {self.account_type} account for {self.owner}")
        if opening_balance:
            self.deposit(opening_balance, "opening balance")

    # ------------------------------------------------------------------ #
    # read-only surface
    # ------------------------------------------------------------------ #
    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def currency(self) -> str:
        return self._currency

    @property
    def balance(self) -> Money:
        """Current balance. READ ONLY -- there must be no setter."""
        return self._balance

    @property
    def ledger(self) -> tuple:
        """Immutable snapshot of the transaction history (a ``tuple``)."""
        return tuple(self._ledger)

    @property
    def is_closed(self) -> bool:
        return self._is_closed

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
        return f"T{next(Account._txn_counter):06d}"

    def _validate(self, amount: Money) -> None:
        """Shared guard for every money movement.

        Raise, in this order:
          1. ``AccountClosedError`` if the account is closed.
          2. ``InvalidAmountError`` if ``amount`` is not a ``Money``.
          3. ``CurrencyMismatchError`` if the currency differs.
          4. ``InvalidAmountError`` if the amount is not strictly positive.
        """
        if self.is_closed:
            raise AccountClosedError(self.account_id)
        if not isinstance(amount, Money):
            raise InvalidAmountError(amount, "amount must be Money")
        if amount.currency != self.currency:
            raise CurrencyMismatchError(self.currency, amount.currency)
        if not amount.is_positive:
            raise InvalidAmountError(amount, "amount must be positive")

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
        self._balance = (
            self._balance + amount if txn_type.is_credit else self._balance - amount
        )
        transaction = Transaction(
            self._next_txn_id(), txn_type, amount, self._balance, description
        )
        self._ledger.append(transaction)
        return transaction

    def deposit(self, amount: Money, description: str = "") -> Transaction:
        """Add money. Returns the ledger entry.

        Raises ``AccountClosedError``, ``InvalidAmountError`` (non-positive or
        wrong type) or ``CurrencyMismatchError`` -- see ``_validate``.
        """
        self._validate(amount)
        return self._apply(TransactionType.DEPOSIT, amount, description)

    def withdraw(self, amount: Money, description: str = "") -> Transaction:
        """Remove money. Returns the ledger entry.

        Validate, then compare ``amount`` against ``withdrawable_balance``.
        If it does not fit: write an audit entry describing the rejection and
        raise ``self._insufficient_funds_error(amount)``. Nothing about the
        balance or ledger may change on a failed withdrawal.
        """
        return self._debit(TransactionType.WITHDRAWAL, amount, description)

    def transfer_out(self, amount: Money, description: str = "") -> Transaction:
        """Debit leg of a transfer -- same rules as ``withdraw`` but the ledger
        entry is a ``TRANSFER_OUT``.

        Share the guard and the limit check with ``withdraw`` (extract a small
        private helper); copy-pasting the body costs marks.
        """
        return self._debit(TransactionType.TRANSFER_OUT, amount, description)

    def transfer_in(self, amount: Money, description: str = "") -> Transaction:
        """Credit leg of a transfer -- same rules as ``deposit`` but the ledger
        entry is a ``TRANSFER_IN``."""
        self._validate(amount)
        return self._apply(TransactionType.TRANSFER_IN, amount, description)

    def _debit(
        self, txn_type: TransactionType, amount: Money, description: str
    ) -> Transaction:
        """Validate and apply a debit that respects the account's limit."""
        self._validate(amount)
        if amount > self.withdrawable_balance:
            self.audit(f"{txn_type.value.lower()} rejected: insufficient funds")
            raise self._insufficient_funds_error(amount)
        return self._apply(txn_type, amount, description)

    def close(self) -> None:
        """Mark the account closed.

        Idempotent: closing twice is fine and raises nothing. A non-zero
        balance is allowed to remain (the Bank decides policy). Write an audit
        entry.
        """
        if not self._is_closed:
            self._is_closed = True
            self.audit("account closed")

    def monthly_fee(self) -> Money:
        """Fee charged at month end. Default: zero of this currency.
        Override in ``CheckingAccount``."""
        return Money.zero(self.currency)

    def statement(self) -> str:
        """Multi-line human statement. Exact layout is up to you; it must
        include the account id, the owner and one line per transaction."""
        lines = [f"Account: {self.account_id}", f"Owner: {self.owner}"]
        lines.extend(
            f"{txn.timestamp.isoformat()} {txn.type.value} {txn.signed_amount} "
            f"balance={txn.balance_after} {txn.description}".rstrip()
            for txn in self._ledger
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # dunders -- MANDATORY
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        """Number of transactions in the ledger, so ``len(account)`` works."""
        return len(self._ledger)

    def __repr__(self) -> str:
        """e.g. ``SavingsAccount(id='SB0001', owner='Asha', balance=INR 5000.00)``.
        Use ``type(self).__name__`` so subclasses need no override."""
        return (
            f"{type(self).__name__}(id={self.account_id!r}, owner={self.owner!r}, "
            f"balance={self.balance})"
        )

    def __eq__(self, other: object) -> bool:
        """Identity is the ``account_id``. Non-Account -> ``NotImplemented``."""
        if not isinstance(other, Account):
            return NotImplemented
        return self.account_id == other.account_id

    def __hash__(self) -> int:
        return hash(self.account_id)

    def __iter__(self):
        """Iterate over the ledger, so ``for txn in account`` works."""
        return iter(self._ledger)

    def to_dict(self) -> Dict[str, Any]:
        """Override of the mixin hook. Required exact keys::

            {"account_id": str, "account_type": str, "owner": str,
             "currency": str, "balance": str, "is_closed": bool,
             "transactions": [ {..transaction dicts..} ]}
        """
        return {
            "account_id": self.account_id,
            "account_type": self.account_type,
            "owner": self.owner,
            "currency": self.currency,
            "balance": str(self.balance.amount),
            "is_closed": self.is_closed,
            "transactions": [txn.to_dict() for txn in self._ledger],
        }


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
        if not self.balance.is_positive:
            return Money.zero(self.currency)
        return self.balance * self.annual_interest_rate * (Decimal(1) / Decimal(12))

    def accrue_monthly_interest(self) -> Optional[Transaction]:
        """Credit one month of interest.

        Return the ``INTEREST`` transaction, or ``None`` when the interest
        works out to zero (no zero-value ledger noise) or the account is
        closed.
        """
        if self.is_closed:
            return None
        interest = self.monthly_interest()
        if not interest:
            return None
        return self._apply(TransactionType.INTEREST, interest, "monthly interest")


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
        candidate_minimum = (
            Money(self.DEFAULT_MINIMUM, currency)
            if minimum_balance is None
            else minimum_balance
        )
        if not isinstance(candidate_minimum, Money):
            raise InvalidAmountError(candidate_minimum, "minimum balance must be Money")
        if candidate_minimum.currency != Money.zero(currency).currency:
            raise CurrencyMismatchError(currency.upper(), candidate_minimum.currency)
        if candidate_minimum.is_negative:
            raise InvalidAmountError(candidate_minimum, "minimum balance cannot be negative")

        rate = self.DEFAULT_RATE if interest_rate is None else interest_rate
        if not isinstance(rate, Decimal):
            raise InvalidAmountError(rate, "interest rate must be Decimal")
        if rate < 0:
            raise InvalidAmountError(rate, "interest rate cannot be negative")

        self._minimum_balance = candidate_minimum
        self._interest_rate = rate
        super().__init__(account_id, owner, currency, opening_balance)

    @property
    def account_type(self) -> str:
        """Return ``"SAVINGS"``."""
        return "SAVINGS"

    @property
    def minimum_balance(self) -> Money:
        return self._minimum_balance

    @property
    def annual_interest_rate(self) -> Decimal:
        return self._interest_rate

    @property
    def withdrawable_balance(self) -> Money:
        """``balance - minimum_balance``, floored at zero."""
        available = self.balance - self.minimum_balance
        return available if available.is_positive else Money.zero(self.currency)

    def _insufficient_funds_error(self, requested: Money) -> InsufficientFundsError:
        return InsufficientFundsError(requested, self.withdrawable_balance)

    def to_dict(self) -> Dict[str, Any]:
        """Base dict PLUS ``"minimum_balance"`` (str) and
        ``"interest_rate"`` (str). Call ``super().to_dict()`` -- do not
        re-build the common keys."""
        result = super().to_dict()
        result.update(
            {
                "minimum_balance": str(self.minimum_balance.amount),
                "interest_rate": str(self.annual_interest_rate),
            }
        )
        return result


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
        candidate_limit = (
            Money(self.DEFAULT_OVERDRAFT, currency)
            if overdraft_limit is None
            else overdraft_limit
        )
        candidate_fee = Money(self.DEFAULT_FEE, currency) if fee is None else fee
        for value, label in (
            (candidate_limit, "overdraft limit"),
            (candidate_fee, "monthly fee"),
        ):
            if not isinstance(value, Money):
                raise InvalidAmountError(value, f"{label} must be Money")
            expected_currency = Money.zero(currency).currency
            if value.currency != expected_currency:
                raise CurrencyMismatchError(expected_currency, value.currency)
            if value.is_negative:
                raise InvalidAmountError(value, f"{label} cannot be negative")
        self._overdraft_limit = candidate_limit
        self._fee = candidate_fee
        super().__init__(account_id, owner, currency, opening_balance)

    @property
    def account_type(self) -> str:
        """Return ``"CHECKING"``."""
        return "CHECKING"

    @property
    def overdraft_limit(self) -> Money:
        return self._overdraft_limit

    @property
    def withdrawable_balance(self) -> Money:
        """``balance + overdraft_limit``."""
        return self.balance + self.overdraft_limit

    def _insufficient_funds_error(self, requested: Money) -> InsufficientFundsError:
        """Return an ``OverdraftLimitExceededError`` carrying the limit."""
        return OverdraftLimitExceededError(
            requested, self.withdrawable_balance, self.overdraft_limit
        )

    def monthly_fee(self) -> Money:
        """Override: the configured fee."""
        return self._fee

    def to_dict(self) -> Dict[str, Any]:
        """Base dict PLUS ``"overdraft_limit"`` and ``"monthly_fee"`` (both str)."""
        result = super().to_dict()
        result.update(
            {
                "overdraft_limit": str(self.overdraft_limit.amount),
                "monthly_fee": str(self.monthly_fee().amount),
            }
        )
        return result
