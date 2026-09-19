"""Exception hierarchy for the Mini Banking & Payments System.

RULES
-----
* Every exception raised by this package MUST derive from :class:`BankError`,
  so a caller can write ``except BankError`` and be sure it caught everything
  the domain can throw.
* Never raise a bare ``Exception`` and never catch with a bare ``except:``.
* When you wrap a lower-level error (e.g. ``decimal.InvalidOperation``),
  chain it with ``raise ... from exc`` so the original traceback survives.

This module is ALREADY COMPLETE. Do not change the class names or the
attribute names -- the test suite imports and inspects them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from minibank.money import Money


class BankError(Exception):
    """Base class for every error raised by the minibank package."""


class CurrencyMismatchError(BankError):
    """Raised when two Money values of different currencies are combined.

    Attributes
    ----------
    left, right:
        The two currency codes that did not match.
    """

    def __init__(self, left: str, right: str) -> None:
        super().__init__(f"cannot combine {left} with {right}")
        self.left = left
        self.right = right


class InvalidAmountError(BankError, ValueError):
    """Raised for an amount that is not usable: negative, zero, or non-numeric.

    Also inherits from ``ValueError`` so that generic numeric-validation code
    keeps working. Attribute ``value`` holds whatever was rejected.
    """

    def __init__(self, value: Any, reason: str = "invalid amount") -> None:
        super().__init__(f"{reason}: {value!r}")
        self.value = value
        self.reason = reason


class InsufficientFundsError(BankError):
    """Raised when a withdrawal exceeds the withdrawable balance.

    Attributes
    ----------
    requested:
        The amount the caller tried to take out.
    available:
        The amount that was actually withdrawable at that moment.
    """

    def __init__(self, requested: "Money", available: "Money") -> None:
        super().__init__(f"requested {requested}, only {available} available")
        self.requested = requested
        self.available = available


class OverdraftLimitExceededError(InsufficientFundsError):
    """Raised when a checking account withdrawal breaches its overdraft limit.

    Subclass of :class:`InsufficientFundsError` on purpose: callers that only
    care about "not enough money" keep working, callers that care about the
    overdraft specifically can catch this narrower type.
    """

    def __init__(self, requested: "Money", available: "Money", limit: "Money") -> None:
        super().__init__(requested, available)
        self.limit = limit


class AccountError(BankError):
    """Base class for account lifecycle problems."""


class AccountNotFoundError(AccountError, KeyError):
    """Raised by ``Bank.get_account`` when the id is unknown."""

    def __init__(self, account_id: str) -> None:
        super().__init__(f"no such account: {account_id!r}")
        self.account_id = account_id


class DuplicateAccountError(AccountError):
    """Raised when opening an account with an id that already exists."""

    def __init__(self, account_id: str) -> None:
        super().__init__(f"account already exists: {account_id!r}")
        self.account_id = account_id


class AccountClosedError(AccountError):
    """Raised when any money movement is attempted on a closed account."""

    def __init__(self, account_id: str) -> None:
        super().__init__(f"account is closed: {account_id!r}")
        self.account_id = account_id


class TransferError(BankError):
    """Raised when a transfer cannot be completed as a whole.

    The original cause MUST be attached via ``raise TransferError(...) from exc``.
    """


class UnknownAccountTypeError(BankError, ValueError):
    """Raised by the Bank factory for an unregistered account type name."""

    def __init__(self, kind: str) -> None:
        super().__init__(f"unknown account type: {kind!r}")
        self.kind = kind


__all__ = [
    "BankError",
    "CurrencyMismatchError",
    "InvalidAmountError",
    "InsufficientFundsError",
    "OverdraftLimitExceededError",
    "AccountError",
    "AccountNotFoundError",
    "DuplicateAccountError",
    "AccountClosedError",
    "TransferError",
    "UnknownAccountTypeError",
]
