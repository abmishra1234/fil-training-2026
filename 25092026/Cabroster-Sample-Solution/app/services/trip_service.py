from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import to_ist
from app.models import Booking, BookingStatus, Cab, Role, Trip, TripStatus, User
from app.schemas import TripCreate
from app.services import rules
from app.services.mappers import seats_booked


def get_trip(db: Session, trip_id: int) -> Trip:
    t = db.get(Trip, trip_id)
    if t is None:
        raise HTTPException(404, detail="Trip not found")
    return t


def _busy(db: Session, column, value, travel_date, slot) -> bool:
    return db.scalar(select(Trip.id).where(
        column == value, Trip.travel_date == travel_date, Trip.slot == slot,
        Trip.status != TripStatus.CANCELLED)) is not None


def create_trip(db: Session, data: TripCreate, now: datetime) -> Trip:
    rules.validate_service_date(data.travel_date, now)
    cab = db.get(Cab, data.cab_id)
    if cab is None:
        raise HTTPException(404, detail="Cab not found")
    driver = db.get(User, data.driver_id)
    if driver is None:
        raise HTTPException(404, detail="Driver not found")
    if not cab.is_active:                                                   # BR-08
        raise HTTPException(422, detail="Cab is inactive")
    if driver.role != Role.DRIVER or not driver.is_active:
        raise HTTPException(422, detail="User is not an active driver")
    if _busy(db, Trip.cab_id, cab.id, data.travel_date, data.slot):         # BR-07
        raise HTTPException(409, detail="Cab already has a trip for this date and slot")
    if _busy(db, Trip.driver_id, driver.id, data.travel_date, data.slot):
        raise HTTPException(409, detail="Driver already has a trip for this date and slot")
    trip = Trip(**data.model_dump(), status=TripStatus.SCHEDULED)
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def assign_bookings(db: Session, trip: Trip, booking_ids: list[int]) -> Trip:
    if trip.status != TripStatus.SCHEDULED:                                 # BR-11
        raise HTTPException(409, detail="Trip is not SCHEDULED")
    bookings = []
    for bid in booking_ids:
        b = db.get(Booking, bid)
        if b is None:
            raise HTTPException(404, detail=f"Booking {bid} not found")
        if b.status != BookingStatus.BOOKED:                                # BR-10
            raise HTTPException(409, detail=f"Booking {bid} is not in BOOKED status")
        if (b.travel_date, b.slot, b.zone) != (trip.travel_date, trip.slot, trip.zone):
            raise HTTPException(409, detail=f"Booking {bid} does not match trip date/slot/zone")
        bookings.append(b)
    used = seats_booked(trip)
    if used + len(bookings) > trip.cab.capacity:                            # BR-09
        raise HTTPException(409, detail=f"Cab capacity exceeded: {used} of {trip.cab.capacity} seats taken, "
                                         f"{len(bookings)} requested")
    for b in bookings:                                                      # all-or-nothing
        b.trip_id = trip.id
        b.status = BookingStatus.ASSIGNED
    db.commit()
    db.refresh(trip)
    return trip


def remove_booking(db: Session, trip: Trip, booking_id: int) -> Trip:
    b = db.get(Booking, booking_id)
    if b is None or b.trip_id != trip.id:
        raise HTTPException(404, detail="Booking not found on this trip")
    if trip.status != TripStatus.SCHEDULED:
        raise HTTPException(409, detail="Trip is not SCHEDULED")
    b.trip_id = None
    b.status = BookingStatus.BOOKED
    db.commit()
    db.refresh(trip)
    return trip


def cancel_trip(db: Session, trip: Trip) -> Trip:
    if trip.status != TripStatus.SCHEDULED:                                 # BR-13
        raise HTTPException(409, detail=f"Cannot cancel a trip in status {trip.status.value}")
    for b in list(trip.bookings):                                           # BR-16
        if b.status != BookingStatus.CANCELLED:
            b.status = BookingStatus.BOOKED
            b.trip_id = None
    trip.status = TripStatus.CANCELLED
    db.commit()
    db.refresh(trip)
    return trip


# ---------- driver ----------
def get_driver_trip(db: Session, driver: User, trip_id: int) -> Trip:
    t = db.get(Trip, trip_id)
    if t is None or t.driver_id != driver.id:                               # BR-12
        raise HTTPException(404, detail="Trip not found")
    return t


def start_trip(db: Session, trip: Trip, now: datetime) -> Trip:
    if trip.status != TripStatus.SCHEDULED:
        raise HTTPException(409, detail=f"Cannot start a trip in status {trip.status.value}")
    now = to_ist(now)
    if now.date() != trip.travel_date or now < rules.start_window_opens(trip.travel_date, trip.slot):
        raise HTTPException(422, detail="Trip can only be started on the travel date from 30 minutes before departure")
    trip.status = TripStatus.IN_PROGRESS
    trip.started_at = now.replace(tzinfo=None)
    db.commit()
    db.refresh(trip)
    return trip


def mark_boarding(db: Session, trip: Trip, booking_id: int, new_status: BookingStatus) -> Booking:
    if trip.status != TripStatus.IN_PROGRESS:                               # BR-14
        raise HTTPException(409, detail="Trip is not IN_PROGRESS")
    b = db.get(Booking, booking_id)
    if b is None or b.trip_id != trip.id:
        raise HTTPException(404, detail="Booking not found on this trip")
    if b.status != BookingStatus.ASSIGNED:
        raise HTTPException(409, detail=f"Booking already marked {b.status.value}")
    b.status = new_status
    db.commit()
    db.refresh(b)
    return b


def complete_trip(db: Session, trip: Trip, now: datetime) -> Trip:
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(409, detail=f"Cannot complete a trip in status {trip.status.value}")
    for b in trip.bookings:                                                 # BR-15
        if b.status == BookingStatus.ASSIGNED:
            b.status = BookingStatus.NO_SHOW
        elif b.status == BookingStatus.BOARDED:
            b.status = BookingStatus.COMPLETED
    trip.status = TripStatus.COMPLETED
    trip.completed_at = to_ist(now).replace(tzinfo=None)
    db.commit()
    db.refresh(trip)
    return trip
