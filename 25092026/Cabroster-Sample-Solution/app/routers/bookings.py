from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, not_, or_, select
from sqlalchemy.orm import Session

from app.core.deps import PageParams, get_now, require_roles
from app.core.query import apply_sort, check_date_range, paginate
from app.database import get_db
from app.models import Booking, BookingStatus, Role, Slot, User, Zone
from app.schemas import BookingCreate, BookingRead, Page
from app.services import booking_service
from app.services.mappers import booking_read

router = APIRouter(prefix="/bookings", tags=["bookings"])
employee_only = require_roles(Role.EMPLOYEE)
admin_only = require_roles(Role.ADMIN)
employee_or_admin = require_roles(Role.EMPLOYEE, Role.ADMIN)


@router.post("", response_model=BookingRead, status_code=201, summary="Book a seat")
def create_booking(data: BookingCreate, user: User = Depends(employee_only),
                   db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    return booking_read(booking_service.create_booking(db, user, data, now))


@router.get("/me", response_model=Page[BookingRead], summary="My bookings")
def my_bookings(
    slot: Optional[Slot] = None, status: Optional[BookingStatus] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    sort_by: Literal["travel_date", "created_at"] = "travel_date",
    order: Literal["asc", "desc"] = "desc",
    pg: PageParams = Depends(), user: User = Depends(employee_only), db: Session = Depends(get_db),
):
    check_date_range(date_from, date_to)
    stmt = select(Booking).where(Booking.employee_id == user.id)
    if slot:
        stmt = stmt.where(Booking.slot == slot)
    if status:
        stmt = stmt.where(Booking.status == status)
    if date_from:
        stmt = stmt.where(Booking.travel_date >= date_from)
    if date_to:
        stmt = stmt.where(Booking.travel_date <= date_to)
    stmt = apply_sort(stmt, sort_by, order, {"travel_date": Booking.travel_date,
                                             "created_at": Booking.created_at}, Booking.id)
    return paginate(db, stmt, pg.page, pg.size, booking_read)


@router.get("", response_model=Page[BookingRead], summary="All bookings (admin)")
def all_bookings(
    travel_date: Optional[date] = None, slot: Optional[Slot] = None, zone: Optional[Zone] = None,
    status: Optional[BookingStatus] = None, employee_id: Optional[int] = None,
    unassigned: Optional[bool] = None, q: Optional[str] = None,
    sort_by: Literal["travel_date", "created_at", "zone"] = "created_at",
    order: Literal["asc", "desc"] = "asc",
    pg: PageParams = Depends(), _=Depends(admin_only), db: Session = Depends(get_db),
):
    stmt = select(Booking).join(User, Booking.employee_id == User.id)
    if travel_date:
        stmt = stmt.where(Booking.travel_date == travel_date)
    if slot:
        stmt = stmt.where(Booking.slot == slot)
    if zone:
        stmt = stmt.where(Booking.zone == zone)
    if status:
        stmt = stmt.where(Booking.status == status)
    if employee_id is not None:
        stmt = stmt.where(Booking.employee_id == employee_id)
    if unassigned is not None:
        cond = and_(Booking.trip_id.is_(None), Booking.status == BookingStatus.BOOKED)
        stmt = stmt.where(cond if unassigned else not_(cond))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.full_name.ilike(like), User.employee_code.ilike(like)))
    stmt = apply_sort(stmt, sort_by, order, {"travel_date": Booking.travel_date, "created_at": Booking.created_at,
                                             "zone": Booking.zone}, Booking.id)
    return paginate(db, stmt, pg.page, pg.size, booking_read)


@router.get("/{booking_id}", response_model=BookingRead, summary="Booking detail")
def get_booking(booking_id: int, user: User = Depends(employee_or_admin), db: Session = Depends(get_db)):
    return booking_read(booking_service.get_visible_booking(db, user, booking_id))


@router.patch("/{booking_id}/cancel", response_model=BookingRead, summary="Cancel booking")
def cancel_booking(booking_id: int, user: User = Depends(employee_or_admin),
                   db: Session = Depends(get_db), now: datetime = Depends(get_now)):
    b = booking_service.get_visible_booking(db, user, booking_id)
    return booking_read(booking_service.cancel_booking(db, user, b, now))
