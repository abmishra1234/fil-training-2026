"""Business rules for scheduled payments (Task 4)."""
from datetime import date
from typing import List, Optional

from fastapi import Depends

from ..core.errors import (AccountNotFoundError, InvalidRequestError,
                           KYCRequiredError, ResourceNotFoundError)
from ..models.scheduled_payment import ScheduledPayment
from ..repositories.account_repository import AccountRepository
from ..repositories.scheduled_payment_repository import ScheduledPaymentRepository
from ..schemas.scheduled_payment_schema import ScheduledPaymentCreate, ScheduledPaymentUpdate


def _ensure_not_past(d: date) -> None:
    if d < date.today():
        raise InvalidRequestError("next_run_date cannot be in the past",
                                  {"next_run_date": str(d), "today": str(date.today())})


class ScheduledPaymentService:
    def __init__(self, repo: ScheduledPaymentRepository = Depends(),
                 account_repo: AccountRepository = Depends()):
        self.repo = repo
        self.account_repo = account_repo

    def create(self, account_id: int, data: ScheduledPaymentCreate) -> ScheduledPayment:
        account = self.account_repo.get_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(account_id)
        if not account.kyc_compliant:                 # re-uses the KYC flag from Extension 4
            raise KYCRequiredError(account_id)
        _ensure_not_past(data.next_run_date)
        payment = ScheduledPayment(account_id=account_id, payee_name=data.payee_name,
                                   payee_account=data.payee_account, amount=data.amount,
                                   frequency=data.frequency.value,
                                   next_run_date=data.next_run_date, status="ACTIVE")
        return self.repo.create(payment)

    def list_for_account(self, account_id: int, status: Optional[str] = None) -> List[ScheduledPayment]:
        if self.account_repo.get_by_id(account_id) is None:
            raise AccountNotFoundError(account_id)
        return self.repo.list_for_account(account_id, status)

    def get(self, payment_id: int) -> ScheduledPayment:
        payment = self.repo.get_by_id(payment_id)
        if payment is None:
            raise ResourceNotFoundError("Scheduled payment not found", {"payment_id": payment_id})
        return payment

    def update(self, payment_id: int, patch: ScheduledPaymentUpdate) -> ScheduledPayment:
        payment = self.get(payment_id)
        changes = patch.model_dump(exclude_unset=True)   # ONLY fields the client sent
        if not changes:
            raise InvalidRequestError("PATCH body must contain at least one field",
                                      {"allowed_fields": ["amount", "next_run_date", "status"]})
        if changes.get("next_run_date") is not None:
            _ensure_not_past(changes["next_run_date"])
        for field, value in changes.items():
            if value is None:
                raise InvalidRequestError(f"'{field}' cannot be null")
            setattr(payment, field, value.value if hasattr(value, "value") else value)
        return self.repo.save(payment)

    def delete(self, payment_id: int) -> None:
        self.repo.delete(self.get(payment_id))
