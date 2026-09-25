from typing import List, Optional
from fastapi import Depends
from ..models.account import Account
from ..models.transaction import Transaction, TransactionType            # Task 2
from ..repositories.account_repository import AccountRepository
from ..repositories.transaction_repository import TransactionRepository  # Task 2
from ..core.errors import InsufficientFundsError                          # Task 5

class AccountService:
    def __init__(self, repo: AccountRepository = Depends(),
                 txn_repo: TransactionRepository = Depends()):            # Task 2
        self.repo = repo
        self.txn_repo = txn_repo

    # ---------- NEW (Task 2): write a ledger row, committed with the balance ----------
    def _record(self, account: Account, txn_type: str, amount: float,
                counterparty_id: Optional[int] = None) -> None:
        self.txn_repo.add(Transaction(account_id=account.id, type=txn_type,
                                      amount=amount, balance_after=account.balance,
                                      counterparty_account_id=counterparty_id))

    def create_account(self, owner_name: str, owner_id: Optional[int] = None) -> Account:
        return self.repo.create(Account(owner_name=owner_name, balance=0.0,
                                        owner_id=owner_id))                 # Ext 6

    def get_account(self, account_id: int) -> Optional[Account]:
        return self.repo.get_by_id(account_id)

    def list_accounts(self, owner_id: Optional[int] = None) -> List[Account]:
        # Ext 6: owner_id=None means "all accounts" (admin view)
        return self.repo.get_all(owner_id)

    def deposit(self, account_id: int, amount: float):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        account = self.repo.get_by_id(account_id)
        if not account:
            return None
        account.balance += amount
        self._record(account, TransactionType.DEPOSIT, amount)          # Task 2
        return self.repo.update(account)

    def withdraw(self, account_id: int, amount: float):
        if amount <= 0:
            raise ValueError("Withdraw amount must be positive")
        account = self.repo.get_by_id(account_id)
        if not account:
            return None
        if account.balance - amount < 0:
            raise InsufficientFundsError(account.balance, amount)       # Task 5
        account.balance -= amount
        self._record(account, TransactionType.WITHDRAWAL, amount)       # Task 2
        return self.repo.update(account)

    # ---------- NEW: Transfer ----------
    def transfer(self, from_id: int, to_id: int, amount: float):
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        if from_id == to_id:
            raise ValueError("Cannot transfer to the same account")
        src = self.repo.get_by_id(from_id)
        dst = self.repo.get_by_id(to_id)
        if not src or not dst:
            return None
        if src.balance - amount < 0:
            raise InsufficientFundsError(src.balance, amount)           # Task 5
        src.balance -= amount
        dst.balance += amount
        self._record(src, TransactionType.TRANSFER_OUT, amount, dst.id) # Task 2
        self._record(dst, TransactionType.TRANSFER_IN, amount, src.id)  # Task 2
        self.repo.update(src)      # ONE commit saves BOTH rows
        return src, dst

    # ---------- NEW: KYC ----------
    def get_kyc_status(self, account_id: int) -> Optional[Account]:
        return self.repo.get_by_id(account_id)

    def set_kyc_compliant(self, account_id: int, flag: bool) -> Optional[Account]:
        account = self.repo.get_by_id(account_id)
        if not account:
            return None
        return self.repo.set_kyc_flag(account, flag)
