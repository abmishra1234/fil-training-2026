"""Driver operations (DEV-14). DRIVER only; a driver sees ONLY own trips (others -> 404)."""
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import PageParams, get_now, require_roles
from app.database import get_db
from app.models import Role, Slot, TripStatus, User
from app.schemas import BoardingUpdate

router = APIRouter(prefix="/driver/trips", tags=["driver"])
driver_only = require_roles(Role.DRIVER)


@router.get("", summary="My trips")
def my_trips(
    travel_date: Optional[date] = None, status: Optional[TripStatus] = None, slot: Optional[Slot] = None,
    sort_by: Literal["travel_date"] = "travel_date", order: Literal["asc", "desc"] = "desc",
    pg: PageParams = Depends(), me: User = Depends(driver_only), db: Session = Depends(get_db),
):
    raise NotImplementedError("DEV-14")


@router.get("/{trip_id}", summary="Trip manifest")
def manifest(trip_id: int, me: User = Depends(driver_only), db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-14")


@router.patch("/{trip_id}/start", summary="Start trip")
def start(trip_id: int, me: User = Depends(driver_only), db: Session = Depends(get_db),
          now: datetime = Depends(get_now)):
    raise NotImplementedError("DEV-14")


@router.patch("/{trip_id}/bookings/{booking_id}", summary="Mark boarded / no-show")
def mark(trip_id: int, booking_id: int, data: BoardingUpdate, me: User = Depends(driver_only),
         db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-14")


@router.patch("/{trip_id}/complete", summary="Complete trip")
def complete(trip_id: int, me: User = Depends(driver_only), db: Session = Depends(get_db),
             now: datetime = Depends(get_now)):
    raise NotImplementedError("DEV-14")
