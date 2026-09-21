from fastapi import Depends # type: ignore
from ..repositories.account_repository import AccountRepository
from ..schemas.account_schema import AccountCreate
from ..models.account import Account

class AccountService:
    def __init__(self, repo: AccountRepository = Depends()):
        self.repo = repo

    def get_account(self, account_id: int):
        return self.repo.get_by_id(account_id)

    def get_all_accounts(self):
        return self.repo.get_all()

    def create_account(self, account_data: AccountCreate) -> Account:
        new_account = Account(owner_name=account_data.owner_name, balance=0.0)
        return self.repo.create(new_account)

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
