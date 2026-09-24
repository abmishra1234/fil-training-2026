from sqlalchemy import Column, Integer, String, Float, Boolean
from ..database import Base

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    owner_name = Column(String, index=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    # NEW (KYC): every new account starts as NOT compliant
    kyc_compliant = Column(Boolean, default=False, nullable=False)
    # TODO Ext6 Task 5: add owner_id -> ForeignKey("users.id"), indexed, nullable=True

