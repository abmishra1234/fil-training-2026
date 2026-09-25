import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ..schemas.account_schema import (AccountCreate, AccountOut,
    TransferRequest, TransferResult, KYCStatusUpdate, KYCStatusOut)
from ..services.account_service import AccountService
from ..services.idempotency_service import IdempotencyService       # Task 6 (ext 5)
from ..core.auth import (AccountAccess, can_operate_account,          # Ext 6
                         can_view_account, get_current_user, require_role)
from ..models.user import Role, User                                  # Ext 6

# Ext 6 - Task 4: router-level dependency -> NO route below is reachable without a valid JWT.
# (Shared by /accounts (legacy) and /api/v1/accounts, so the legacy door is locked too.)
router = APIRouter(prefix="/accounts", tags=["Accounts"],
                   dependencies=[Depends(get_current_user)])

class AmountRequest(BaseModel):
    amount: float

@router.post("/", response_model=AccountOut)
def create_account(payload: AccountCreate, service: AccountService = Depends(),
                   user: User = Depends(get_current_user)):
    return service.create_account(payload.owner_name, owner_id=user.id)       # Ext 6 - Task 5

@router.get("/", response_model=List[AccountOut])
def list_accounts(service: AccountService = Depends(),
                  user: User = Depends(get_current_user)):
    # Ext 6 - Task 6: ADMIN sees every account, a CUSTOMER only their own.
    return service.list_accounts(owner_id=None if user.role == Role.ADMIN else user.id)

# ---------- Transfer (+ Task 6: optional Idempotency-Key) ----------
@router.post("/transfer", response_model=TransferResult)
def transfer_money(request: TransferRequest, http_request: Request,
                   service: AccountService = Depends(),
                   idem: IdempotencyService = Depends(),
                   access: AccountAccess = Depends(),                              # Ext 6
                   idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    # Ext 6 - Task 5: you may only send money FROM an account you own.
    # (The destination can be anyone's - that's the point of a transfer.)
    access.operate(request.from_account_id)

    endpoint = http_request.url.path
    payload = request.model_dump()
    # Ext 6: scope keys per user, so two users picking the same key never collide
    # or see each other's cached responses.
    scoped_key = f"user:{access.user.id}:{idempotency_key}" if idempotency_key else None

    # Replay? -> return the ORIGINAL response, move no money.
    if scoped_key:
        record = idem.lookup(scoped_key, endpoint, payload)
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

    if scoped_key:                     # remember successful outcomes only
        idem.remember(scoped_key, endpoint, payload, 200, body)
    return body

@router.get("/{account_id}", response_model=AccountOut,
            dependencies=[Depends(can_view_account)])                       # Ext 6
def get_account(account_id: int, service: AccountService = Depends()):
    account = service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.post("/{account_id}/deposit", response_model=AccountOut,
             dependencies=[Depends(can_operate_account)])                   # Ext 6
def deposit_money(account_id: int, request: AmountRequest,
                  service: AccountService = Depends()):
    try:
        updated = service.deposit(account_id, request.amount)
        if not updated:
            raise HTTPException(status_code=404, detail="Account not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{account_id}/withdraw", response_model=AccountOut,
             dependencies=[Depends(can_operate_account)])                   # Ext 6
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
@router.get("/{account_id}/kyc-status", response_model=KYCStatusOut,
            dependencies=[Depends(can_view_account)])                       # Ext 6
def get_kyc_status(account_id: int, service: AccountService = Depends()):
    account = service.get_kyc_status(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account.id, "kyc_compliant": account.kyc_compliant}

# Ext 6 - Task 6: customers must NOT be able to self-certify KYC -> ADMIN only.
@router.put("/{account_id}/kyc-status", response_model=KYCStatusOut,
            dependencies=[Depends(require_role(Role.ADMIN))])
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
