"""A person who can log in to the API (Extension 6 - Task 1)."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from ..database import Base
from .transaction import utcnow


class Role:
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)   # stored lower-case
    hashed_password = Column(String, nullable=False)                     # NEVER the plain password
    role = Column(String, default=Role.CUSTOMER, nullable=False)         # CUSTOMER | ADMIN
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
