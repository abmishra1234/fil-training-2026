"""Task 6 -- the Bank orchestrator.

Responsibilities:
  * a FACTORY that creates accounts from a type name (``@classmethod`` +
    a registry, not a chain of ``if``s);
  * a registry/lookup of accounts;
  * ATOMIC transfers;
  * aggregate reporting (``total_assets``);
  * month-end processing driven by a duck-typed strategy.

The Bank never touches ``account._balance``. It only calls the public account
API -- that is what makes encapsulation real rather than decorative.
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type

from minibank.accounts import Account, CheckingAccount, SavingsAccount
from minibank.exceptions import (
    AccountClosedError,
    AccountNotFoundError,
    BankError,
    CurrencyMismatchError,
    DuplicateAccountError,
    InsufficientFundsError,
    InvalidAmountError,
    TransferError,
    UnknownAccountTypeError,
)
from minibank.mixins import JSONSerializableMixin
from minibank.money import DEFAULT_CURRENCY, Money
from minibank.transaction import Transaction, TransactionType


class Bank(JSONSerializableMixin):
    """Holds accounts and coordinates operations across them.

    Parameters
    ----------
    name:
        Bank name, non-empty.
    currency:
        The bank's base currency. ``total_assets`` is reported in it and
        accounts of a different currency are excluded from that total.

    Class attributes
    ----------------
    ACCOUNT_TYPES:
        The factory registry: ``{"SAVINGS": SavingsAccount,
        "CHECKING": CheckingAccount}``. Extend it with
        :meth:`register_account_type` -- adding a new account type must NOT
        require editing ``open_account`` (open/closed principle).
    """

    ACCOUNT_TYPES: Dict[str, Type[Account]] = {}

    def __init__(self, name: str, currency: str = DEFAULT_CURRENCY) -> None:
        """Validate ``name``, set up the empty account map and an id counter."""
        if not isinstance(name, str) or not name.strip():
            raise ValueError("bank name must be non-empty")
        self._name = name.strip()
        self._currency = Money.zero(currency).currency
        self._accounts: Dict[str, Account] = {}
        self._id_counters: Dict[str, itertools.count] = {}

    @property
    def name(self) -> str:
        """The bank's display name."""
        return self._name

    @property
    def currency(self) -> str:
        """The bank's base currency."""
        return self._currency

    # ------------------------------------------------------------------ #
    # factory
    # ------------------------------------------------------------------ #
    @classmethod
    def register_account_type(cls, kind: str, account_cls: Type[Account]) -> None:
        """Add/replace an entry in ``ACCOUNT_TYPES``.

        ``kind`` is upper-cased. ``account_cls`` must be a subclass of
        ``Account``, otherwise ``TypeError``.
        """
        if not isinstance(account_cls, type) or not issubclass(account_cls, Account):
            raise TypeError("account_cls must be an Account subclass")
        cls.ACCOUNT_TYPES[str(kind).upper()] = account_cls

    @staticmethod
    def validate_account_id(account_id: str) -> str:
        """Return the id upper-cased after checking its shape.

        Valid shape: 2 letters followed by 4 digits, e.g. ``"SB0001"``.
        Anything else -> ``ValueError``. A ``@staticmethod`` because it needs
        neither instance nor class state -- that is the point of the task.
        """
        if not isinstance(account_id, str) or re.fullmatch(
            r"[A-Za-z]{2}\d{4}", account_id
        ) is None:
            raise ValueError(f"invalid account id: {account_id!r}")
        return account_id.upper()

    def _next_account_id(self, kind: str) -> str:
        """``"SB0001"`` for SAVINGS, ``"CH0001"`` for CHECKING: first two
        letters of a per-kind prefix plus a zero-padded counter."""
        prefix = {"SAVINGS": "SB", "CHECKING": "CH"}.get(kind, kind[:2])
        counter = self._id_counters.setdefault(kind, itertools.count(1))
        return f"{prefix}{next(counter):04d}"

    def open_account(
        self,
        kind: str,
        owner: str,
        opening_balance: Optional[Money] = None,
        **kwargs: Any,
    ) -> Account:
        """FACTORY. Create, register and return an account.

        * ``kind`` is matched case-insensitively against ``ACCOUNT_TYPES``;
          unknown -> ``UnknownAccountTypeError``.
        * Extra ``kwargs`` are forwarded to the concrete class, so
          ``open_account("CHECKING", "Ravi", overdraft_limit=Money("10000"))``
          works without the Bank knowing what a checking account is.
        * ``opening_balance`` of a foreign currency -> ``CurrencyMismatchError``.
        * A generated id that somehow already exists -> ``DuplicateAccountError``.
        """
        normalized_kind = str(kind).upper()
        account_cls = self.ACCOUNT_TYPES.get(normalized_kind)
        if account_cls is None:
            raise UnknownAccountTypeError(normalized_kind)

        account_currency = kwargs.pop("currency", self.currency)
        normalized_currency = Money.zero(account_currency).currency
        if opening_balance is not None:
            if not isinstance(opening_balance, Money):
                raise InvalidAmountError(opening_balance, "opening balance must be Money")
            if opening_balance.currency != normalized_currency:
                raise CurrencyMismatchError(normalized_currency, opening_balance.currency)

        account_id = self._next_account_id(normalized_kind)
        if account_id in self._accounts:
            raise DuplicateAccountError(account_id)
        account = account_cls(
            account_id,
            owner,
            currency=normalized_currency,
            opening_balance=opening_balance,
            **kwargs,
        )
        self._accounts[account_id] = account
        return account

    # ------------------------------------------------------------------ #
    # lookup
    # ------------------------------------------------------------------ #
    def get_account(self, account_id: str) -> Account:
        """Return the account or raise ``AccountNotFoundError``.
        Lookup is case-insensitive."""
        key = account_id.upper() if isinstance(account_id, str) else account_id
        try:
            return self._accounts[key]
        except KeyError as exc:
            raise AccountNotFoundError(str(account_id).upper()) from exc

    def close_account(self, account_id: str) -> Account:
        """Close and return the account. Unknown id -> ``AccountNotFoundError``.
        The account stays in the registry (audit history is not deleted)."""
        account = self.get_account(account_id)
        account.close()
        return account

    @property
    def accounts(self) -> tuple:
        """Immutable snapshot of all accounts, in insertion order."""
        return tuple(self._accounts.values())

    def accounts_of(self, kind: str) -> tuple:
        """All accounts whose ``account_type`` matches ``kind`` (case-insensitive)."""
        normalized = str(kind).upper()
        return tuple(
            account for account in self._accounts.values()
            if account.account_type.upper() == normalized
        )

    # ------------------------------------------------------------------ #
    # operations
    # ------------------------------------------------------------------ #
    def transfer(
        self,
        from_id: str,
        to_id: str,
        amount: Money,
        description: str = "",
    ) -> Tuple[Transaction, Transaction]:
        """Move money between two accounts ATOMICALLY.

        Returns ``(debit_txn, credit_txn)`` -- a ``TRANSFER_OUT`` on the source
        and a ``TRANSFER_IN`` on the destination.

        Rules
        -----
        * ``from_id == to_id`` -> ``TransferError`` (nothing is recorded).
        * Either account closed -> ``AccountClosedError``.
        * Currency mismatch between the two accounts -> ``CurrencyMismatchError``.
        * If the source cannot afford it, the ``InsufficientFundsError`` from
          ``withdraw`` propagates unchanged and NOTHING is recorded anywhere.
        * ATOMICITY: if the debit succeeds but the credit then fails for any
          ``BankError``, you must put the money back on the source (a
          compensating ``TRANSFER_IN``) and raise ``TransferError`` chained
          from the original with ``raise TransferError(...) from exc``.

        Implementation hint: use the public ``account.transfer_out`` /
        ``account.transfer_in`` methods (never ``_apply`` or ``_balance``) and
        wrap the credit leg in ``try/except BankError``. The rollback is a
        ``transfer_in`` back onto the source.
        """
        if str(from_id).upper() == str(to_id).upper():
            raise TransferError("cannot transfer to the same account")
        source = self.get_account(from_id)
        destination = self.get_account(to_id)
        if source.is_closed:
            raise AccountClosedError(source.account_id)
        if destination.is_closed:
            raise AccountClosedError(destination.account_id)
        if source.currency != destination.currency:
            raise CurrencyMismatchError(source.currency, destination.currency)

        debit = source.transfer_out(amount, description)
        try:
            credit = destination.transfer_in(amount, description)
        except BankError as exc:
            source.transfer_in(amount, f"rollback: {description}".rstrip())
            raise TransferError("transfer credit failed; debit rolled back") from exc
        return debit, credit

    def total_assets(self) -> Money:
        """Sum the balances of all OPEN accounts in the bank's base currency.

        Accounts in another currency are skipped (no FX in this exercise).
        An empty bank returns ``Money.zero(self.currency)``.
        Build the sum with ``functools.reduce`` or a plain loop over
        ``Money.__add__`` -- do not touch ``Decimal`` directly.
        """
        total = Money.zero(self.currency)
        for account in self._accounts.values():
            if not account.is_closed and account.currency == self.currency:
                total = total + account.balance
        return total

    def monthly_process(self, strategy: object) -> Dict[str, List[Transaction]]:
        """Run ``strategy`` over every account. DUCK TYPING.

        * First validate the shape: the object must have a callable ``apply``
          and a ``name``. If not -> ``TypeError`` with a message that says what
          was missing. Do NOT require a particular base class.
        * Then return ``{account_id: [transactions the strategy created]}``,
          including accounts where the list came back empty.
        * A ``BankError`` from one account must not abort the whole run: record
          it in that account's audit trail and carry on with the next account.
        """
        apply = getattr(strategy, "apply", None)
        if not callable(apply):
            raise TypeError("strategy is missing a callable apply method")
        if not hasattr(strategy, "name"):
            raise TypeError("strategy is missing a name")

        results: Dict[str, List[Transaction]] = {}
        for account in self._accounts.values():
            try:
                results[account.account_id] = apply(account)
            except BankError as exc:
                account.audit(f"{getattr(strategy, 'name')} failed: {exc}")
                results[account.account_id] = []
        return results

    # ------------------------------------------------------------------ #
    # dunders
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        """Number of accounts."""
        return len(self._accounts)

    def __contains__(self, account_id: object) -> bool:
        """``"SB0001" in bank``. Accept an id string or an ``Account``."""
        if isinstance(account_id, Account):
            return account_id.account_id in self._accounts
        if isinstance(account_id, str):
            return account_id.upper() in self._accounts
        return False

    def __iter__(self) -> Iterator[Account]:
        return iter(self._accounts.values())

    def __getitem__(self, account_id: str) -> Account:
        """``bank["SB0001"]`` -- same behaviour as ``get_account``."""
        return self.get_account(account_id)

    def __repr__(self) -> str:
        """e.g. ``Bank(name='FIL Bank', accounts=3, assets=INR 12500.00)``."""
        return (
            f"Bank(name={self.name!r}, accounts={len(self)}, "
            f"assets={self.total_assets()})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Required exact keys::

            {"name": str, "currency": str, "total_assets": str,
             "accounts": [ {..account dicts..} ]}
        """
        return {
            "name": self.name,
            "currency": self.currency,
            "total_assets": str(self.total_assets().amount),
            "accounts": [account.to_dict() for account in self._accounts.values()],
        }


# Register the two built-in types. Keep this at import time so the factory
# works without extra setup.
Bank.ACCOUNT_TYPES.update({"SAVINGS": SavingsAccount, "CHECKING": CheckingAccount})
