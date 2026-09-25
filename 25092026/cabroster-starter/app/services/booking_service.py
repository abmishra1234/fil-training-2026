"""Booking business rules (DEV-09, DEV-10). Keep routers thin — put the rules here."""
from datetime import datetime

from fastapi import HTTPException  # noqa: F401
from sqlalchemy.orm import Session

from app.models import Booking, User
from app.services import rules  # noqa: F401


def create_booking(db: Session, user: User, data, now: datetime) -> Booking:
    """TODO: BR-01, BR-02 (rules.validate_service_date), BR-05 (profile complete), BR-04 (cut-off),
    BR-03 (one active booking per employee/date/slot -> 409).
    Copy zone and home_address from the user (snapshot). Status BOOKED."""
    raise NotImplementedError("DEV-09")


def get_visible_booking(db: Session, user: User, booking_id: int) -> Booking:
    """TODO: 404 if missing, or if an EMPLOYEE asks for someone else's booking."""
    raise NotImplementedError("DEV-10")


def cancel_booking(db: Session, user: User, b: Booking, now: datetime) -> Booking:
    """TODO (BR-06): only BOOKED/ASSIGNED (else 409); trip must still be SCHEDULED (else 409);
    employees bound by the cancellation cut-off (422), admins are not.
    Set CANCELLED, cancelled_at, trip_id = None (frees the seat)."""
    raise NotImplementedError("DEV-10")
