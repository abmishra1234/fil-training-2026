"""Mini Banking & Payments System -- Python OOP + Exception Handling exercise.

Public API. This file is complete; you only implement the modules it imports.
"""

from minibank.accounts import (
    Account,
    CheckingAccount,
    InterestBearingAccount,
    SavingsAccount,
)
from minibank.bank import Bank
from minibank.exceptions import (
    AccountClosedError,
    AccountError,
    AccountNotFoundError,
    BankError,
    CurrencyMismatchError,
    DuplicateAccountError,
    InsufficientFundsError,
    InvalidAmountError,
    OverdraftLimitExceededError,
    TransferError,
    UnknownAccountTypeError,
)
from minibank.mixins import AuditableMixin, JSONSerializableMixin
from minibank.money import Money
from minibank.strategies import (
    CompositeStrategy,
    InterestStrategy,
    MaintenanceFeeStrategy,
)
from minibank.transaction import Transaction, TransactionType

__version__ = "1.0.0"

__all__ = [
    "Money",
    "Transaction",
    "TransactionType",
    "Account",
    "InterestBearingAccount",
    "SavingsAccount",
    "CheckingAccount",
    "Bank",
    "JSONSerializableMixin",
    "AuditableMixin",
    "InterestStrategy",
    "MaintenanceFeeStrategy",
    "CompositeStrategy",
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
