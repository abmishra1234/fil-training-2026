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
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # factory
    # ------------------------------------------------------------------ #
    @classmethod
    def register_account_type(cls, kind: str, account_cls: Type[Account]) -> None:
        """Add/replace an entry in ``ACCOUNT_TYPES``.

        ``kind`` is upper-cased. ``account_cls`` must be a subclass of
        ``Account``, otherwise ``TypeError``.
        """
        raise NotImplementedError("TODO")

    @staticmethod
    def validate_account_id(account_id: str) -> str:
        """Return the id upper-cased after checking its shape.

        Valid shape: 2 letters followed by 4 digits, e.g. ``"SB0001"``.
        Anything else -> ``ValueError``. A ``@staticmethod`` because it needs
        neither instance nor class state -- that is the point of the task.
        """
        raise NotImplementedError("TODO")

    def _next_account_id(self, kind: str) -> str:
        """``"SB0001"`` for SAVINGS, ``"CH0001"`` for CHECKING: first two
        letters of a per-kind prefix plus a zero-padded counter."""
        raise NotImplementedError("TODO")

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
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # lookup
    # ------------------------------------------------------------------ #
    def get_account(self, account_id: str) -> Account:
        """Return the account or raise ``AccountNotFoundError``.
        Lookup is case-insensitive."""
        raise NotImplementedError("TODO")

    def close_account(self, account_id: str) -> Account:
        """Close and return the account. Unknown id -> ``AccountNotFoundError``.
        The account stays in the registry (audit history is not deleted)."""
        raise NotImplementedError("TODO")

    @property
    def accounts(self) -> tuple:
        """Immutable snapshot of all accounts, in insertion order."""
        raise NotImplementedError("TODO")

    def accounts_of(self, kind: str) -> tuple:
        """All accounts whose ``account_type`` matches ``kind`` (case-insensitive)."""
        raise NotImplementedError("TODO")

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
        raise NotImplementedError("TODO")

    def total_assets(self) -> Money:
        """Sum the balances of all OPEN accounts in the bank's base currency.

        Accounts in another currency are skipped (no FX in this exercise).
        An empty bank returns ``Money.zero(self.currency)``.
        Build the sum with ``functools.reduce`` or a plain loop over
        ``Money.__add__`` -- do not touch ``Decimal`` directly.
        """
        raise NotImplementedError("TODO")

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
        raise NotImplementedError("TODO")

    # ------------------------------------------------------------------ #
    # dunders
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        """Number of accounts."""
        raise NotImplementedError("TODO")

    def __contains__(self, account_id: object) -> bool:
        """``"SB0001" in bank``. Accept an id string or an ``Account``."""
        raise NotImplementedError("TODO")

    def __iter__(self) -> Iterator[Account]:
        raise NotImplementedError("TODO")

    def __getitem__(self, account_id: str) -> Account:
        """``bank["SB0001"]`` -- same behaviour as ``get_account``."""
        raise NotImplementedError("TODO")

    def __repr__(self) -> str:
        """e.g. ``Bank(name='FIL Bank', accounts=3, assets=INR 12500.00)``."""
        raise NotImplementedError("TODO")

    def to_dict(self) -> Dict[str, Any]:
        """Required exact keys::

            {"name": str, "currency": str, "total_assets": str,
             "accounts": [ {..account dicts..} ]}
        """
        raise NotImplementedError("TODO")


# Register the two built-in types. Keep this at import time so the factory
# works without extra setup.
Bank.ACCOUNT_TYPES.update({"SAVINGS": SavingsAccount, "CHECKING": CheckingAccount})
