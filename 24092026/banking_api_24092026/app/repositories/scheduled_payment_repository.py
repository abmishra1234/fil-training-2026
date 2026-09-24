"""Data access for scheduled payments (Task 4)."""
from typing import List, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.scheduled_payment import ScheduledPayment


class ScheduledPaymentRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def create(self, payment: ScheduledPayment) -> ScheduledPayment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get_by_id(self, payment_id: int) -> Optional[ScheduledPayment]:
        return self.db.query(ScheduledPayment).filter(ScheduledPayment.id == payment_id).first()

    def list_for_account(self, account_id: int, status: Optional[str] = None) -> List[ScheduledPayment]:
        q = self.db.query(ScheduledPayment).filter(ScheduledPayment.account_id == account_id)
        if status is not None:
            q = q.filter(ScheduledPayment.status == status)
        return q.order_by(ScheduledPayment.next_run_date.asc(), ScheduledPayment.id.asc()).all()

    def save(self, payment: ScheduledPayment) -> ScheduledPayment:
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def delete(self, payment: ScheduledPayment) -> None:
        self.db.delete(payment)
        self.db.commit()
