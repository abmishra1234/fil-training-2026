from typing import List
from fastapi import APIRouter, Depends, HTTPException # type: ignore
from pydantic import BaseModel # type: ignore
from ..services.account_service import AccountService
from ..schemas.account_schema import AccountCreate, AccountOut

router = APIRouter(prefix="/accounts", tags=["Accounts"])

@router.post("/", response_model=AccountOut)
def create_account(account_data: AccountCreate, service: AccountService = Depends()):
    return service.create_account(account_data)

@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, service: AccountService = Depends()):
    account = service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.get("/", response_model=List[AccountOut])
def get_all_accounts(service: AccountService = Depends()):
    return service.get_all_accounts()

class AmountRequest(BaseModel):
    amount: float

@router.post("/{account_id}/deposit", response_model=AccountOut)
def deposit_money(account_id: int, request: AmountRequest, service: AccountService = Depends()):
    try:
        updated_account = service.deposit(account_id, request.amount)
        if not updated_account:
            raise HTTPException(status_code=404, detail="Account not found")
        return updated_account
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{account_id}/withdraw", response_model=AccountOut)
def withdraw_money(account_id: int, request: AmountRequest, service: AccountService = Depends()):
    try:
        updated_account = service.withdraw(account_id, request.amount)
        if not updated_account:
            raise HTTPException(status_code=404, detail="Account not found")
        return updated_account
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
