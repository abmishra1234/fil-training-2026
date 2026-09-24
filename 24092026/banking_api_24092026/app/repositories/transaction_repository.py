"""Data access for transactions (Tasks 2-3)."""
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.transaction import Transaction

SORTABLE_COLUMNS = {"created_at": Transaction.created_at, "amount": Transaction.amount}


class TransactionRepository:
    def __init__(self, db: Session = Depends(get_db)):
        # FastAPI caches get_db per request, so this is the SAME session the
        # AccountRepository uses -> one commit saves balance + ledger row.
        self.db = db

    def add(self, txn: Transaction) -> None:
        """Stage a row. The caller's commit (AccountRepository.update) persists it."""
        self.db.add(txn)

    def search(self, account_id: int, *, txn_type: Optional[str],
               min_amount: Optional[float], max_amount: Optional[float],
               start: Optional[datetime], end_exclusive: Optional[datetime],
               sort_field: str, descending: bool,
               offset: int, limit: int) -> Tuple[List[Transaction], int]:
        q = self.db.query(Transaction).filter(Transaction.account_id == account_id)
        # 1) FILTER - only add a WHERE clause for params the client actually sent
        if txn_type is not None:
            q = q.filter(Transaction.type == txn_type)
        if min_amount is not None:
            q = q.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            q = q.filter(Transaction.amount <= max_amount)
        if start is not None:
            q = q.filter(Transaction.created_at >= start)
        if end_exclusive is not None:
            q = q.filter(Transaction.created_at < end_exclusive)

        total = q.count()                      # count BEFORE paginating

        # 2) SORT - whitelisted column + id tie-breaker for stable pages
        column = SORTABLE_COLUMNS[sort_field]
        id_col = Transaction.id
        q = q.order_by(column.desc() if descending else column.asc(),
                       id_col.desc() if descending else id_col.asc())

        # 3) PAGINATE
        items = q.offset(offset).limit(limit).all()
        return items, total
