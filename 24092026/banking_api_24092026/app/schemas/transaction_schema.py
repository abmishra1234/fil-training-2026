"""Transaction list contract (Tasks 2-3)."""
from datetime import datetime
from enum import Enum
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class TransactionTypeEnum(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class TransactionOut(BaseModel):
    id: int
    account_id: int
    type: TransactionTypeEnum
    amount: float
    balance_after: float
    counterparty_account_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """Standard envelope for every paginated collection."""
    items: List[T]
    page: int
    limit: int
    total: int
    total_pages: int
