"""Scheduled payments: one resource, five verbs (Task 4). v1 only.

  POST   /accounts/{account_id}/scheduled-payments   -> 201 + Location
  GET    /accounts/{account_id}/scheduled-payments   -> 200 list
  GET    /scheduled-payments/{payment_id}            -> 200 | 404
  PATCH  /scheduled-payments/{payment_id}            -> 200 (partial update)
  DELETE /scheduled-payments/{payment_id}            -> 204 | 404
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status

from ..core.auth import (AccountAccess, can_operate_account,   # Ext 6
                         can_view_account, get_current_user)
from ..schemas.scheduled_payment_schema import (PaymentStatus, ScheduledPaymentCreate,
                                                ScheduledPaymentOut, ScheduledPaymentUpdate)
from ..services.scheduled_payment_service import ScheduledPaymentService

# Ext 6: every route needs a valid token
router = APIRouter(tags=["Scheduled Payments"], dependencies=[Depends(get_current_user)])


@router.post("/accounts/{account_id}/scheduled-payments",
             response_model=ScheduledPaymentOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(can_operate_account)])        # Ext 6: owner only
def create_scheduled_payment(account_id: int, payload: ScheduledPaymentCreate,
                             response: Response,
                             service: ScheduledPaymentService = Depends()):
    payment = service.create(account_id, payload)
    response.headers["Location"] = f"/api/v1/scheduled-payments/{payment.id}"
    return payment


@router.get("/accounts/{account_id}/scheduled-payments",
            response_model=List[ScheduledPaymentOut],
            dependencies=[Depends(can_view_account)])            # Ext 6: owner or admin
def list_scheduled_payments(account_id: int,
                            status_filter: Optional[PaymentStatus] = Query(None, alias="status"),
                            service: ScheduledPaymentService = Depends()):
    return service.list_for_account(account_id, status_filter.value if status_filter else None)


@router.get("/scheduled-payments/{payment_id}", response_model=ScheduledPaymentOut)
def get_scheduled_payment(payment_id: int, service: ScheduledPaymentService = Depends(),
                          access: AccountAccess = Depends()):
    payment = service.get(payment_id)
    access.view(payment.account_id)       # Ext 6: no path account_id here -> check via the parent
    return payment


@router.patch("/scheduled-payments/{payment_id}", response_model=ScheduledPaymentOut)
def update_scheduled_payment(payment_id: int, patch: ScheduledPaymentUpdate,
                             service: ScheduledPaymentService = Depends(),
                             access: AccountAccess = Depends()):
    access.operate(service.get(payment_id).account_id)           # Ext 6
    return service.update(payment_id, patch)


@router.delete("/scheduled-payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_payment(payment_id: int, service: ScheduledPaymentService = Depends(),
                             access: AccountAccess = Depends()):
    access.operate(service.get(payment_id).account_id)           # Ext 6
    service.delete(payment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
