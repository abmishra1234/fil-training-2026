import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ..schemas.account_schema import (AccountCreate, AccountOut,
    TransferRequest, TransferResult, KYCStatusUpdate, KYCStatusOut)
from ..services.account_service import AccountService
from ..services.idempotency_service import IdempotencyService       # Task 6

# TODO Ext6 Task 4: add a router-level dependency so NO route here works without a valid JWT.
# TODO Ext6 Task 5: create_account must record the owner; list_accounts shows only my accounts;
#                   get/deposit/withdraw/kyc GET/transfer must check ownership (AccountAccess).
#                   Scope the Idempotency-Key per user.
# TODO Ext6 Task 6: PUT kyc-status is ADMIN-only; an ADMIN's GET / lists every account.
router = APIRouter(prefix="/accounts", tags=["Accounts"])

class AmountRequest(BaseModel):
    amount: float

@router.post("/", response_model=AccountOut)
def create_account(payload: AccountCreate, service: AccountService = Depends()):
    return service.create_account(payload.owner_name)

@router.get("/", response_model=List[AccountOut])
def list_accounts(service: AccountService = Depends()):
    return service.list_accounts()

# ---------- Transfer (+ Task 6: optional Idempotency-Key) ----------
@router.post("/transfer", response_model=TransferResult)
def transfer_money(request: TransferRequest, http_request: Request,
                   service: AccountService = Depends(),
                   idem: IdempotencyService = Depends(),
                   idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    endpoint = http_request.url.path
    payload = request.model_dump()

    # Replay? -> return the ORIGINAL response, move no money.
    if idempotency_key:
        record = idem.lookup(idempotency_key, endpoint, payload)
        if record is not None:
            return JSONResponse(status_code=record.status_code,
                                content=json.loads(record.response_body),
                                headers={"Idempotent-Replayed": "true"})
    try:
        result = service.transfer(request.from_account_id,
                                  request.to_account_id, request.amount)
        if not result:
            raise HTTPException(status_code=404, detail="Account not found")
        src, dst = result
        body = TransferResult.model_validate(
            {"from_account": src, "to_account": dst}, from_attributes=True).model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if idempotency_key:                     # remember successful outcomes only
        idem.remember(idempotency_key, endpoint, payload, 200, body)
    return body

@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, service: AccountService = Depends()):
    account = service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.post("/{account_id}/deposit", response_model=AccountOut)
def deposit_money(account_id: int, request: AmountRequest,
                  service: AccountService = Depends()):
    try:
        updated = service.deposit(account_id, request.amount)
        if not updated:
            raise HTTPException(status_code=404, detail="Account not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{account_id}/withdraw", response_model=AccountOut)
def withdraw_money(account_id: int, request: AmountRequest,
                   service: AccountService = Depends()):
    try:
        updated = service.withdraw(account_id, request.amount)
        if not updated:
            raise HTTPException(status_code=404, detail="Account not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------- NEW: KYC ----------
@router.get("/{account_id}/kyc-status", response_model=KYCStatusOut)
def get_kyc_status(account_id: int, service: AccountService = Depends()):
    account = service.get_kyc_status(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account.id, "kyc_compliant": account.kyc_compliant}

@router.put("/{account_id}/kyc-status", response_model=KYCStatusOut)
def set_kyc_status(account_id: int,
                   payload: Optional[KYCStatusUpdate] = None,
                   kyc_compliant: Optional[bool] = Query(None),
                   service: AccountService = Depends()):
    # Priority: 1) JSON body  2) query parameter  3) default True
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
