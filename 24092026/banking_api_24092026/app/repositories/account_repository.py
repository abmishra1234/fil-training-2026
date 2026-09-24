from typing import List, Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.account import Account

class AccountRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get_by_id(self, account_id: int) -> Optional[Account]:
        return self.db.query(Account).filter(Account.id == account_id).first()

    # TODO Ext6 Task 5: optional owner_id filter - do it in SQL, not in Python
    def get_all(self) -> List[Account]:
        return self.db.query(Account).all()

    def create(self, account: Account) -> Account:
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update(self, account: Account) -> Account:
        self.db.commit()
        self.db.refresh(account)
        return account

    # ---------- NEW: KYC ----------
    def set_kyc_flag(self, account: Account, flag: bool) -> Account:
        account.kyc_compliant = flag
        self.db.commit()
        self.db.refresh(account)
        return account
