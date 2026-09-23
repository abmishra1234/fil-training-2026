from datetime import datetime
from typing import List, Optional
from fastapi import Depends # type: ignore
from sqlalchemy.orm import Session # type: ignore
from ..database import get_db
from ..models.account import Account
from ..models.transfer_history import TransferHistory

class AccountRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get_by_id(self, account_id: int) -> Optional[Account]:
        return self.db.query(Account).filter(Account.id == account_id).first()

    def get_all(self) -> List[Account]:
        return self.db.query(Account).all()

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
    ) -> tuple[List[TransferHistory], int]:
        query = self.db.query(TransferHistory)
        if from_account_id is not None:
            query = query.filter(TransferHistory.from_account_id == from_account_id)
        if to_account_id is not None:
            query = query.filter(TransferHistory.to_account_id == to_account_id)
        if transfer_status is not None:
            query = query.filter(TransferHistory.transfer_status == transfer_status)
        if min_amount is not None:
            query = query.filter(TransferHistory.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(TransferHistory.amount <= max_amount)
        if start_timestamp is not None:
            query = query.filter(TransferHistory.timestamp >= start_timestamp)
        if end_timestamp is not None:
            query = query.filter(TransferHistory.timestamp <= end_timestamp)

        total = query.count()
        sort_column = getattr(TransferHistory, sort_by)
        sort_expression = (
            sort_column.desc() if sort_order == "desc" else sort_column.asc()
        )
        transfers = (
            query.order_by(sort_expression, TransferHistory.transfer_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return transfers, total

    def create(self, account: Account) -> Account:
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update(self, account: Account) -> Account:
        self.db.commit()
        self.db.refresh(account)
        return account

    def set_kyc_flag(self, account: Account, flag: bool) -> Account:
        account.kyc_compliant = flag
        self.db.commit()
        self.db.refresh(account)
        return account

    def create_transfer_history(self, history: TransferHistory) -> TransferHistory:
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history
