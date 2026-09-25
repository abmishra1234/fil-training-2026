"""Bookings (DEV-09 … DEV-11). Note: /bookings/me MUST be declared before /bookings/{booking_id}."""
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import PageParams, get_now, require_roles
from app.database import get_db
from app.models import BookingStatus, Role, Slot, User, Zone
from app.schemas import BookingCreate

router = APIRouter(prefix="/bookings", tags=["bookings"])
employee_only = require_roles(Role.EMPLOYEE)
admin_only = require_roles(Role.ADMIN)
employee_or_admin = require_roles(Role.EMPLOYEE, Role.ADMIN)


@router.post("", status_code=201, summary="Book a seat")
def create_booking(data: BookingCreate, user: User = Depends(employee_only),
                   db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    raise NotImplementedError("DEV-09")


@router.get("/me", summary="My bookings")
def my_bookings(
    slot: Optional[Slot] = None, status: Optional[BookingStatus] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    sort_by: Literal["travel_date", "created_at"] = "travel_date",
    order: Literal["asc", "desc"] = "desc",
    pg: PageParams = Depends(), user: User = Depends(employee_only), db: Session = Depends(get_db),
):
    raise NotImplementedError("DEV-10")


@router.get("", summary="All bookings (admin)")
def all_bookings(
    travel_date: Optional[date] = None, slot: Optional[Slot] = None, zone: Optional[Zone] = None,
    status: Optional[BookingStatus] = None, employee_id: Optional[int] = None,
    unassigned: Optional[bool] = None, q: Optional[str] = None,
    sort_by: Literal["travel_date", "created_at", "zone"] = "created_at",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), _=Depends(admin_only), db: Session = Depends(get_db),
):
    raise NotImplementedError("DEV-11")


@router.get("/{booking_id}", summary="Booking detail")
def get_booking(booking_id: int, user: User = Depends(employee_or_admin), db: Session = Depends(get_db)):
    raise NotImplementedError("DEV-10")


@router.patch("/{booking_id}/cancel", summary="Cancel booking")
def cancel_booking(booking_id: int, user: User = Depends(employee_or_admin),
                   db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    raise NotImplementedError("DEV-10")
