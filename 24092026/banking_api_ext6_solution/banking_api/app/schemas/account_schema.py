from typing import Optional
from pydantic import BaseModel, ConfigDict

class AccountCreate(BaseModel):
    owner_name: str

class AccountOut(BaseModel):
    id: int
    owner_name: str
    balance: float
    model_config = ConfigDict(from_attributes=True)

# ---------- NEW: Transfer ----------
class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float

class TransferResult(BaseModel):
    from_account: AccountOut
    to_account: AccountOut

# ---------- NEW: KYC ----------
class KYCStatusUpdate(BaseModel):
    kyc_compliant: bool = True      # empty body {} means "mark compliant"

class KYCStatusOut(BaseModel):
    account_id: int
    kyc_compliant: bool
