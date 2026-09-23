from datetime import datetime
from typing import Optional

from fastapi import Depends # type: ignore
from ..repositories.account_repository import AccountRepository
from ..schemas.account_schema import AccountCreate
from ..models.account import Account
from ..models.transfer_history import TransferHistory

class AccountService:
    def __init__(self, repo: AccountRepository = Depends()):
        self.repo = repo

    def get_account(self, account_id: int):
        return self.repo.get_by_id(account_id)

    def get_all_accounts(self):
        return self.repo.get_all()

    def get_all_transfers(
        self,
        from_account_id: Optional[int],
        to_account_id: Optional[int],
        transfer_status: Optional[str],
        min_amount: Optional[float],
        max_amount: Optional[float],
        start_timestamp: Optional[datetime],
        end_timestamp: Optional[datetime],
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ):
        return self.repo.get_all_transfers(
            from_account_id,
            to_account_id,
            transfer_status,
            min_amount,
            max_amount,
            start_timestamp,
            end_timestamp,
            sort_by,
            sort_order,
            page,
            page_size,
        )

    def create_account(self, account_data: AccountCreate) -> Account:
        new_account = Account(
            owner_name=account_data.owner_name,
            balance=account_data.balance,
        )
        return self.repo.create(new_account)

    def transfer(self, from_id: int, to_id: int, amount: float):
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        if from_id == to_id:
            raise ValueError("Cannot transfer to the same account")

        source_account = self.repo.get_by_id(from_id)
        destination_account = self.repo.get_by_id(to_id)
        if not source_account or not destination_account:
            return None
        if source_account.balance - amount < 0:
            raise ValueError("Insufficient funds")

        source_account.balance -= amount
        destination_account.balance += amount
        self.repo.create_transfer_history(
            TransferHistory(
                from_account_id=source_account.id,
                to_account_id=destination_account.id,
                amount=amount,
                transfer_status="SUCCESS",
            )
        )
        return source_account, destination_account

    def get_kyc_status(self, account_id: int):
        return self.repo.get_by_id(account_id)

    def set_kyc_compliant(self, account_id: int, flag: bool):
        account = self.repo.get_by_id(account_id)
        if not account:
            return None
        return self.repo.set_kyc_flag(account, flag)

    def deposit(self, account_id: int, amount: float):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        account = self.repo.get_by_id(account_id)
        if not account:
            return None
        account.balance += amount
        return self.repo.update(account)

    def withdraw(self, account_id: int, amount: float):
        if amount <= 0:
            raise ValueError("Withdraw amount must be positive")
        account = self.repo.get_by_id(account_id)
        if not account:
            return None
        if account.balance - amount < 0:
            raise ValueError("Insufficient funds")
        account.balance -= amount
        return self.repo.update(account)
