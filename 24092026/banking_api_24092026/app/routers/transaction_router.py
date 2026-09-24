"""GET /api/v1/accounts/{account_id}/transactions (Task 3). v1 only."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..schemas.transaction_schema import Page, TransactionOut, TransactionTypeEnum
from ..services.transaction_service import DEFAULT_SORT, TransactionService

# TODO Ext6 Task 4 + 5: token required; only the owner (or an ADMIN) may read the history.
router = APIRouter(prefix="/accounts", tags=["Transactions"])


@router.get("/{account_id}/transactions", response_model=Page[TransactionOut])
def list_transactions(
    account_id: int,
    # ---- filtering ----
    type: Optional[TransactionTypeEnum] = Query(None, description="DEPOSIT | WITHDRAWAL | TRANSFER_IN | TRANSFER_OUT"),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    from_date: Optional[date] = Query(None, description="Inclusive, YYYY-MM-DD"),
    to_date: Optional[date] = Query(None, description="Inclusive, YYYY-MM-DD"),
    # ---- sorting ----
    sort_by: str = Query(DEFAULT_SORT, description="created_at|amount : asc|desc"),
    # ---- pagination ----
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),        # default 25, hard max 100
    service: TransactionService = Depends(),
):
    return service.list_transactions(
        account_id, txn_type=type.value if type else None,
        min_amount=min_amount, max_amount=max_amount,
        from_date=from_date, to_date=to_date,
        sort_by=sort_by, page=page, limit=limit)
