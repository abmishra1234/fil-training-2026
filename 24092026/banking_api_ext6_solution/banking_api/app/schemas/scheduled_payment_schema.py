"""Scheduled payment contract (Task 4)."""
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Frequency(str, Enum):
    ONCE = "ONCE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class PaymentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class ScheduledPaymentCreate(BaseModel):
    payee_name: str = Field(min_length=1, max_length=100)
    payee_account: str = Field(min_length=4, max_length=34)
    amount: float = Field(gt=0)
    frequency: Frequency
    next_run_date: date


class ScheduledPaymentUpdate(BaseModel):
    """PATCH body: every field optional; only the ones sent are changed."""
    amount: Optional[float] = Field(default=None, gt=0)
    next_run_date: Optional[date] = None
    status: Optional[PaymentStatus] = None


class ScheduledPaymentOut(BaseModel):
    id: int
    account_id: int
    payee_name: str
    payee_account: str
    amount: float
    frequency: Frequency
    next_run_date: date
    status: PaymentStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
