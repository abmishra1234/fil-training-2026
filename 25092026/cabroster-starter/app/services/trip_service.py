"""Trip and driver business rules (DEV-12 … DEV-15)."""
from datetime import datetime

from fastapi import HTTPException  # noqa: F401
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, Trip, User  # noqa: F401
from app.services import rules  # noqa: F401


def get_trip(db: Session, trip_id: int) -> Trip:
    """TODO: 404 if not found."""
    raise NotImplementedError("DEV-12")


def create_trip(db: Session, data, now: datetime) -> Trip:
    """TODO: BR-01/02 date rules (422); cab/driver missing (404); inactive cab or non-active-DRIVER (422);
    BR-07 cab or driver already on a non-cancelled trip for the same date+slot (409)."""
    raise NotImplementedError("DEV-12")


def assign_bookings(db: Session, trip: Trip, booking_ids: list[int]) -> Trip:
    """TODO: BR-11 trip must be SCHEDULED (409); each booking exists (404), is BOOKED (409) and matches
    date/slot/zone (409); BR-09 capacity (409). ALL-OR-NOTHING: validate everything before changing anything."""
    raise NotImplementedError("DEV-13")


def remove_booking(db: Session, trip: Trip, booking_id: int) -> Trip:
    """TODO: booking must be on this trip (404); trip SCHEDULED (409); booking back to BOOKED, trip_id None."""
    raise NotImplementedError("DEV-13")


def cancel_trip(db: Session, trip: Trip) -> Trip:
    """TODO (BR-13, BR-16): only from SCHEDULED; non-cancelled bookings go back to BOOKED with trip_id None."""
    raise NotImplementedError("DEV-15")


def get_driver_trip(db: Session, driver: User, trip_id: int) -> Trip:
    """TODO (BR-12): 404 if missing OR not this driver's trip."""
    raise NotImplementedError("DEV-14")


def start_trip(db: Session, trip: Trip, now: datetime) -> Trip:
    """TODO: SCHEDULED only (409); on travel date from 30 min before departure (else 422); set started_at."""
    raise NotImplementedError("DEV-14")


def mark_boarding(db: Session, trip: Trip, booking_id: int, new_status) -> Booking:
    """TODO (BR-14): trip IN_PROGRESS (409); booking on this trip (404); booking ASSIGNED (409)."""
    raise NotImplementedError("DEV-14")


def complete_trip(db: Session, trip: Trip, now: datetime) -> Trip:
    """TODO (BR-15): IN_PROGRESS only (409); ASSIGNED -> NO_SHOW, BOARDED -> COMPLETED; set completed_at."""
    raise NotImplementedError("DEV-14")
