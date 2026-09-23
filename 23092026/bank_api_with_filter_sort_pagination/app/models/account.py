from sqlalchemy import Boolean, CheckConstraint, Column, Float, Integer, String  # type: ignore
from ..database import Base

class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "length(owner_name) BETWEEN 3 AND 50",
            name="ck_accounts_owner_name_length",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_name = Column(String(50), index=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    kyc_compliant = Column(Boolean, default=False, nullable=False)
