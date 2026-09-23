from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field  # type: ignore

class AccountCreate(BaseModel):
    owner_name: str = Field(min_length=3, max_length=50)
    balance: float = Field(default=0.0, ge=0)

class AccountOut(BaseModel):
    id: int
    owner_name: str
    balance: float
    model_config = ConfigDict(from_attributes=True)


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float


class TransferResult(BaseModel):
    from_account: AccountOut
    to_account: AccountOut


class KYCStatusUpdate(BaseModel):
    kyc_compliant: bool = True


class KYCStatusOut(BaseModel):
    account_id: int
    kyc_compliant: bool


class TransferHistoryOut(BaseModel):
    transfer_id: int
    from_account_id: int
    to_account_id: int
    amount: float
    timestamp: datetime
    transfer_status: str
    model_config = ConfigDict(from_attributes=True)
