"""Trips & assignment (DEV-12, DEV-13, DEV-15). ADMIN only."""
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import PageParams, get_now, require_roles
from app.database import get_db
from app.models import Role, Slot, TripStatus, Zone
from app.schemas import AssignRequest, TripCreate

router = APIRouter(prefix="/trips", tags=["trips"], dependencies=[Depends(require_roles(Role.ADMIN))])


@router.post("", status_code=201, summary="Create trip")
def create_trip(data: TripCreate, db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    raise NotImplementedError("DEV-12")


@router.get("", summary="List trips")
def list_trips(
    travel_date: Optional[date] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
    slot: Optional[Slot] = None, zone: Optional[Zone] = None, status: Optional[TripStatus] = None,
    driver_id: Optional[int] = None, cab_id: Optional[int] = None,
    sort_by: Literal["travel_date", "created_at"] = "travel_date",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), db: Session = Depends(get_db),
):
    raise NotImplementedError("DEV-12")


@router.get("/{trip_id}", summary="Trip detail")
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-12")


@router.post("/{trip_id}/bookings", summary="Assign bookings to trip")
def assign(trip_id: int, data: AssignRequest, db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-13")


@router.delete("/{trip_id}/bookings/{booking_id}", summary="Remove booking from trip")
def remove(trip_id: int, booking_id: int, db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-13")


@router.patch("/{trip_id}/cancel", summary="Cancel trip")
def cancel(trip_id: int, db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-15")
