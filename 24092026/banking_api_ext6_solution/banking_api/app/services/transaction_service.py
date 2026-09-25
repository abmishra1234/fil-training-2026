"""Business rules for listing transactions (Task 3)."""
import math
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import Depends

from ..core.errors import AccountNotFoundError, InvalidRequestError
from ..repositories.account_repository import AccountRepository
from ..repositories.transaction_repository import SORTABLE_COLUMNS, TransactionRepository

DEFAULT_SORT = "created_at:desc"


def parse_sort(sort_by: str):
    """'amount:asc' -> ('amount', False). Rejects anything not whitelisted."""
    field, _, direction = sort_by.partition(":")
    direction = (direction or "asc").lower()
    if field not in SORTABLE_COLUMNS or direction not in ("asc", "desc"):
        raise InvalidRequestError(
            f"Invalid sort_by '{sort_by}'",
            {"allowed_fields": sorted(SORTABLE_COLUMNS), "allowed_directions": ["asc", "desc"],
             "example": DEFAULT_SORT})
    return field, direction == "desc"


class TransactionService:
    def __init__(self, repo: TransactionRepository = Depends(),
                 account_repo: AccountRepository = Depends()):
        self.repo = repo
        self.account_repo = account_repo

    def list_transactions(self, account_id: int, *, txn_type: Optional[str] = None,
                          min_amount: Optional[float] = None, max_amount: Optional[float] = None,
                          from_date: Optional[date] = None, to_date: Optional[date] = None,
                          sort_by: str = DEFAULT_SORT, page: int = 1, limit: int = 25) -> dict:
        if self.account_repo.get_by_id(account_id) is None:
            raise AccountNotFoundError(account_id)

        # Cross-field validation: FastAPI can't express these on single params.
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise InvalidRequestError("min_amount cannot be greater than max_amount",
                                      {"min_amount": min_amount, "max_amount": max_amount})
        if from_date and to_date and from_date > to_date:
            raise InvalidRequestError("from_date cannot be after to_date",
                                      {"from_date": str(from_date), "to_date": str(to_date)})

        sort_field, descending = parse_sort(sort_by)
        start = datetime.combine(from_date, time.min) if from_date else None
        # to_date is inclusive for humans -> '< next midnight' for the database
        end_exclusive = datetime.combine(to_date + timedelta(days=1), time.min) if to_date else None

        items, total = self.repo.search(
            account_id, txn_type=txn_type, min_amount=min_amount, max_amount=max_amount,
            start=start, end_exclusive=end_exclusive, sort_field=sort_field,
            descending=descending, offset=(page - 1) * limit, limit=limit)

        return {"items": items, "page": page, "limit": limit, "total": total,
                "total_pages": math.ceil(total / limit) if total else 0}
