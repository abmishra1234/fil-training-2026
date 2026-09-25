"""Ledger entry written for every money movement (Task 2)."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from ..database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)   # stored as naive UTC


class TransactionType:
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True, nullable=False)
    type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    counterparty_account_id = Column(Integer, nullable=True)   # only for transfers
    created_at = Column(DateTime, default=utcnow, index=True, nullable=False)
