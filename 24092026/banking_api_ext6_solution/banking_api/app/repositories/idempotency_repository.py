"""Data access for idempotency records (Task 6)."""
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def get(self, key: str) -> Optional[IdempotencyRecord]:
        return self.db.get(IdempotencyRecord, key)

    def save(self, record: IdempotencyRecord) -> None:
        self.db.add(record)
        self.db.commit()
