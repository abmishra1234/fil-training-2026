from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response # type: ignore
from pydantic import BaseModel # type: ignore
from ..services.account_service import AccountService
from ..schemas.account_schema import (
    AccountCreate,
    AccountOut,
    KYCStatusOut,
    KYCStatusUpdate,
    TransferHistoryOut,
    TransferRequest,
    TransferResult,
)

router = APIRouter(prefix="/accounts", tags=["Accounts"])

@router.post("/", response_model=AccountOut, status_code=201)
def create_account(account_data: AccountCreate, service: AccountService = Depends()):
    return service.create_account(account_data)

@router.get("/transfers", response_model=List[TransferHistoryOut])
def get_all_transfers(
    response: Response,
    from_account_id: Optional[int] = Query(None),
    to_account_id: Optional[int] = Query(None),
    transfer_status: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    start_timestamp: Optional[datetime] = Query(None),
    end_timestamp: Optional[datetime] = Query(None),
    sort_by: Literal["transfer_id", "timestamp", "amount", "transfer_status"] = "timestamp",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    service: AccountService = Depends(),
):
    transfers, total = service.get_all_transfers(
        from_account_id,
        to_account_id,
        transfer_status,
        min_amount,
        max_amount,
        start_timestamp,
        end_timestamp,
        sort_by,
        sort_order,
        page,
        page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Total-Pages"] = str((total + page_size - 1) // page_size)
    return transfers

@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, service: AccountService = Depends()):
    account = service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.get("/", response_model=List[AccountOut])
def get_all_accounts(service: AccountService = Depends()):
    return service.get_all_accounts()

@router.post("/transfer", response_model=TransferResult)
def transfer_money(request: TransferRequest, service: AccountService = Depends()):
    try:
        result = service.transfer(
            request.from_account_id,
            request.to_account_id,
            request.amount,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Account not found")
        source_account, destination_account = result
        return {
            "from_account": source_account,
            "to_account": destination_account,
        }
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@router.get("/{account_id}/kyc-status", response_model=KYCStatusOut)
def get_kyc_status(account_id: int, service: AccountService = Depends()):
    account = service.get_kyc_status(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account.id, "kyc_compliant": account.kyc_compliant}

@router.put("/{account_id}/kyc-status", response_model=KYCStatusOut)
def set_kyc_status(
    account_id: int,
    payload: Optional[KYCStatusUpdate] = None,
    kyc_compliant: Optional[bool] = Query(None),
    service: AccountService = Depends(),
):
    if payload is not None:
        flag = payload.kyc_compliant
    elif kyc_compliant is not None:
        flag = kyc_compliant
    else:
        flag = True

    account = service.set_kyc_compliant(account_id, flag)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account.id, "kyc_compliant": account.kyc_compliant}

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
