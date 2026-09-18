"""Task 5 -- month-end strategies (duck typing, no base class).

A "strategy" here is ANY object with this shape::

    class SomeStrategy:
        name: str
        def apply(self, account) -> list[Transaction]: ...

``Bank.monthly_process`` accepts anything that quacks like that. There is
deliberately NO abstract base class: the point of the task is to show that
Python does not need one, while still validating the shape up front with
``hasattr`` (see ``Bank.monthly_process``).

Every ``apply`` MUST:
  * return a list (possibly empty) of the transactions it created;
  * skip closed accounts, returning ``[]``;
  * never raise for a normal no-op (nothing to do -> empty list).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from minibank.accounts import Account, InterestBearingAccount
from minibank.transaction import Transaction, TransactionType


class InterestStrategy:
    """Credit one month of interest to every interest-bearing account."""

    name = "interest"

    def apply(self, account: Account) -> List[Transaction]:
        """Accrue interest if -- and only if -- the account is an
        ``InterestBearingAccount`` and is open.

        Use ``isinstance(account, InterestBearingAccount)`` here: this is the
        one place where an explicit type check is the RIGHT call, because the
        capability is defined by the abstract class. Anything else -> ``[]``.
        """
        raise NotImplementedError("TODO")


class MaintenanceFeeStrategy:
    """Charge each account's ``monthly_fee()``.

    Rules:
      * a fee of zero or less is a no-op -> ``[]`` (savings has no fee);
      * a fee must never break the account's own rules, so charge it through
        ``account.withdraw``, not ``_apply``;
      * if the withdrawal is refused (``InsufficientFundsError``), swallow THAT
        SPECIFIC exception, write an audit entry mentioning the fee, and
        return ``[]`` -- never a bare ``except``.
    """

    name = "maintenance-fee"

    def apply(self, account: Account) -> List[Transaction]:
        raise NotImplementedError("TODO")


class CompositeStrategy:
    """Run several strategies in order and concatenate their results.

    Demonstrates composition beating inheritance: no strategy subclasses
    another, they are just held in a list.

    >>> month_end = CompositeStrategy(InterestStrategy(), MaintenanceFeeStrategy())
    >>> month_end.name
    'interest+maintenance-fee'
    """

    def __init__(self, *strategies: object) -> None:
        """Store the strategies. Reject any object missing ``apply`` with
        ``TypeError``."""
        raise NotImplementedError("TODO")

    @property
    def name(self) -> str:
        """The child names joined with ``"+"``."""
        raise NotImplementedError("TODO")

    def apply(self, account: Account) -> List[Transaction]:
        raise NotImplementedError("TODO")
