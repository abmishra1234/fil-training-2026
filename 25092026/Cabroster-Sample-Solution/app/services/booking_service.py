from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import to_ist
from app.models import Booking, BookingStatus, Role, TripStatus, User
from app.schemas import BookingCreate
from app.services import rules


def create_booking(db: Session, user: User, data: BookingCreate, now: datetime) -> Booking:
    rules.validate_service_date(data.travel_date, now)                      # BR-01, BR-02
    if not user.home_address or not user.zone:                              # BR-05
        raise HTTPException(422, detail="Complete your profile (home_address and zone) before booking")
    if to_ist(now) >= rules.booking_cutoff(data.travel_date, data.slot):    # BR-04
        raise HTTPException(422, detail="Booking window closed")
    dup = db.scalar(select(Booking.id).where(                               # BR-03
        Booking.employee_id == user.id, Booking.travel_date == data.travel_date,
        Booking.slot == data.slot, Booking.status != BookingStatus.CANCELLED))
    if dup:
        raise HTTPException(409, detail="You already have an active booking for this date and slot")
    booking = Booking(
        employee_id=user.id, travel_date=data.travel_date, slot=data.slot, zone=user.zone,
        pickup_drop_address=user.home_address, status=BookingStatus.BOOKED,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_visible_booking(db: Session, user: User, booking_id: int) -> Booking:
    b = db.get(Booking, booking_id)
    if b is None or (user.role == Role.EMPLOYEE and b.employee_id != user.id):
        raise HTTPException(404, detail="Booking not found")
    return b


def cancel_booking(db: Session, user: User, b: Booking, now: datetime) -> Booking:
    if b.status not in (BookingStatus.BOOKED, BookingStatus.ASSIGNED):
        raise HTTPException(409, detail=f"Booking cannot be cancelled in status {b.status.value}")
    if b.trip is not None and b.trip.status != TripStatus.SCHEDULED:
        raise HTTPException(409, detail="Trip has already started")
    if user.role == Role.EMPLOYEE and to_ist(now) >= rules.cancel_cutoff(b.travel_date, b.slot):  # BR-06
        raise HTTPException(422, detail="Cancellation window closed")
    b.status = BookingStatus.CANCELLED
    b.cancelled_at = to_ist(now).replace(tzinfo=None)
    b.trip_id = None
    db.commit()
    db.refresh(b)
    return b
