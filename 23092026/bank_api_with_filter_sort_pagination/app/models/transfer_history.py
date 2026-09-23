from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func  # type: ignore

from ..database import Base


class TransferHistory(Base):
    __tablename__ = "transfer_history"

    transfer_id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    transfer_status = Column(String(20), nullable=False, default="SUCCESS")
