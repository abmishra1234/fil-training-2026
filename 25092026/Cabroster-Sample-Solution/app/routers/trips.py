from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import PageParams, get_now, require_roles
from app.core.query import apply_sort, check_date_range, paginate
from app.database import get_db
from app.models import Role, Slot, Trip, TripStatus, Zone
from app.schemas import AssignRequest, Page, TripCreate, TripDetail, TripRead
from app.services import trip_service
from app.services.mappers import trip_detail, trip_read

router = APIRouter(prefix="/trips", tags=["trips"], dependencies=[Depends(require_roles(Role.ADMIN))])


@router.post("", response_model=TripRead, status_code=201, summary="Create trip")
def create_trip(data: TripCreate, db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    return trip_read(trip_service.create_trip(db, data, now))


@router.get("", response_model=Page[TripRead], summary="List trips")
def list_trips(
    travel_date: Optional[date] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
    slot: Optional[Slot] = None, zone: Optional[Zone] = None, status: Optional[TripStatus] = None,
    driver_id: Optional[int] = None, cab_id: Optional[int] = None,
    sort_by: Literal["travel_date", "created_at"] = "travel_date",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), db: Session = Depends(get_db),
):
    check_date_range(date_from, date_to)
    stmt = select(Trip)
    for col, val in ((Trip.travel_date, travel_date), (Trip.slot, slot), (Trip.zone, zone),
                     (Trip.status, status), (Trip.driver_id, driver_id), (Trip.cab_id, cab_id)):
        if val is not None:
            stmt = stmt.where(col == val)
    if date_from:
        stmt = stmt.where(Trip.travel_date >= date_from)
    if date_to:
        stmt = stmt.where(Trip.travel_date <= date_to)
    stmt = apply_sort(stmt, sort_by, order, {"travel_date": Trip.travel_date, "created_at": Trip.created_at}, Trip.id)
    return paginate(db, stmt, pg.page, pg.size, trip_read)


@router.get("/{trip_id}", response_model=TripDetail, summary="Trip detail")
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    return trip_detail(trip_service.get_trip(db, trip_id))


@router.post("/{trip_id}/bookings", response_model=TripDetail, summary="Assign bookings to trip")
def assign(trip_id: int, data: AssignRequest, db: Session = Depends(get_db)):
    trip = trip_service.get_trip(db, trip_id)
    return trip_detail(trip_service.assign_bookings(db, trip, data.booking_ids))


@router.delete("/{trip_id}/bookings/{booking_id}", response_model=TripDetail, summary="Remove booking from trip")
def remove(trip_id: int, booking_id: int, db: Session = Depends(get_db)):
    trip = trip_service.get_trip(db, trip_id)
    return trip_detail(trip_service.remove_booking(db, trip, booking_id))


@router.patch("/{trip_id}/cancel", response_model=TripDetail, summary="Cancel trip")
def cancel(trip_id: int, db: Session = Depends(get_db)):
    return trip_detail(trip_service.cancel_trip(db, trip_service.get_trip(db, trip_id)))
