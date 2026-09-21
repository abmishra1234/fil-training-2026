from sqlalchemy import Column, Integer, String, Float # type: ignore
from ..database import Base

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    owner_name = Column(String, index=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
