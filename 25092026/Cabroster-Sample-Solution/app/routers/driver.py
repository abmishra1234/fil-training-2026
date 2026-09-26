from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import PageParams, get_now, require_roles
from app.core.query import apply_sort, paginate
from app.database import get_db
from app.models import Role, Slot, Trip, TripStatus, User
from app.schemas import BoardingUpdate, BookingRead, Page, TripDetail, TripRead
from app.services import trip_service
from app.services.mappers import booking_read, trip_detail, trip_read

router = APIRouter(prefix="/driver/trips", tags=["driver"])
driver_only = require_roles(Role.DRIVER)


@router.get("", response_model=Page[TripRead], summary="My trips")
def my_trips(
    travel_date: Optional[date] = None, status: Optional[TripStatus] = None, slot: Optional[Slot] = None,
    sort_by: Literal["travel_date"] = "travel_date", order: Literal["asc", "desc"] = "desc",
    pg: PageParams = Depends(), me: User = Depends(driver_only), db: Session = Depends(get_db),
):
    stmt = select(Trip).where(Trip.driver_id == me.id)
    for col, val in ((Trip.travel_date, travel_date), (Trip.status, status), (Trip.slot, slot)):
        if val is not None:
            stmt = stmt.where(col == val)
    stmt = apply_sort(stmt, sort_by, order, {"travel_date": Trip.travel_date}, Trip.id)
    return paginate(db, stmt, pg.page, pg.size, trip_read)


@router.get("/{trip_id}", response_model=TripDetail, summary="Trip manifest")
def manifest(trip_id: int, me: User = Depends(driver_only), db: Session = Depends(get_db)):
    return trip_detail(trip_service.get_driver_trip(db, me, trip_id))


@router.patch("/{trip_id}/start", response_model=TripDetail, summary="Start trip")
def start(trip_id: int, me: User = Depends(driver_only), db: Session = Depends(get_db),
          now: datetime = Depends(get_now)):
    trip = trip_service.get_driver_trip(db, me, trip_id)
    return trip_detail(trip_service.start_trip(db, trip, now))


@router.patch("/{trip_id}/bookings/{booking_id}", response_model=BookingRead, summary="Mark boarded / no-show")
def mark(trip_id: int, booking_id: int, data: BoardingUpdate, me: User = Depends(driver_only),
         db: Session = Depends(get_db)):
    trip = trip_service.get_driver_trip(db, me, trip_id)
    return booking_read(trip_service.mark_boarding(db, trip, booking_id, data.status))


@router.patch("/{trip_id}/complete", response_model=TripDetail, summary="Complete trip")
def complete(trip_id: int, me: User = Depends(driver_only), db: Session = Depends(get_db),
             now: datetime = Depends(get_now)):
    trip = trip_service.get_driver_trip(db, me, trip_id)
    return trip_detail(trip_service.complete_trip(db, trip, now))
