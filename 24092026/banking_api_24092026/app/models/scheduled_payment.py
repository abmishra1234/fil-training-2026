"""Standing instruction to pay a payee in the future (Task 4)."""
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String

from ..database import Base
from .transaction import utcnow


class ScheduledPayment(Base):
    __tablename__ = "scheduled_payments"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True, nullable=False)
    payee_name = Column(String, nullable=False)
    payee_account = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    frequency = Column(String, nullable=False)        # ONCE | WEEKLY | MONTHLY
    next_run_date = Column(Date, nullable=False)
    status = Column(String, default="ACTIVE", nullable=False)   # ACTIVE | PAUSED
    created_at = Column(DateTime, default=utcnow, nullable=False)
