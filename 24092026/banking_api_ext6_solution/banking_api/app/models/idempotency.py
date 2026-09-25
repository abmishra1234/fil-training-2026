"""Remembers the response for each Idempotency-Key (Task 6)."""
from sqlalchemy import Column, DateTime, Integer, String, Text

from ..database import Base
from .transaction import utcnow


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_keys"
    key = Column(String, primary_key=True)
    endpoint = Column(String, nullable=False)
    request_hash = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False)       # JSON string
    created_at = Column(DateTime, default=utcnow, nullable=False)
