"""Pydantic v2 schemas.

DONE for you : Page[T], UserRead, Token (use them as patterns).
YOUR TASK    : fill every class marked TODO. Field lists and rules are in spec sections 4 and 6.
"""
import re  # noqa: F401
from datetime import date, datetime
from typing import Generic, List, Literal, Optional, TypeVar  # noqa: F401

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator  # noqa: F401

from app.models import BookingStatus, Role, Slot, TripStatus, Zone  # noqa: F401

T = TypeVar("T")
PHONE = r"^[6-9]\d{9}$"
REG_NO = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str
    role: Role
    employee_code: Optional[str]
    home_address: Optional[str]
    zone: Optional[Zone]
    license_no: Optional[str]
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


# ---------------------------------------------------------------- TODO: users / auth
class UserRegister(BaseModel):
    """TODO: full_name(2-100), email(EmailStr, lower-cased), phone(PHONE), password(min 8, 1 letter + 1 digit),
    employee_code(1-20), home_address(optional, max 255), zone(optional Zone)."""


class UserCreateByAdmin(BaseModel):
    """TODO: same base fields + role (DRIVER|ADMIN only) + license_no (required when DRIVER)."""


class ProfileUpdate(BaseModel):
    """TODO: phone, home_address, zone — all optional."""


class UserStatusUpdate(BaseModel):
    """TODO: is_active: bool"""


# ---------------------------------------------------------------- TODO: cabs
class CabCreate(BaseModel):
    """TODO: registration_no (upper-case, REG_NO regex), model (1-50), capacity (1-12)."""


class CabUpdate(BaseModel):
    """TODO: model, capacity, is_active — all optional."""


class CabRead(BaseModel):
    """TODO: id, registration_no, model, capacity, is_active, created_at."""


# ---------------------------------------------------------------- TODO: bookings
class BookingCreate(BaseModel):
    """TODO: travel_date: date, slot: Slot"""


class TripSummary(BaseModel):
    """TODO: id, status, cab_registration_no, driver_name, driver_phone"""


class BookingRead(BaseModel):
    """TODO: id, employee_id, travel_date, slot, zone, pickup_drop_address, status, trip_id,
    trip (TripSummary | None), created_at, cancelled_at"""


# ---------------------------------------------------------------- TODO: trips
class TripCreate(BaseModel):
    """TODO: travel_date, slot, zone, cab_id, driver_id"""


class TripRead(BaseModel):
    """TODO: id, travel_date, slot, zone, cab_id, driver_id, status, seats_booked, seats_available,
    started_at, completed_at, created_at"""


class TripDetail(TripRead):
    """TODO: TripRead + cab (CabRead), driver {id, full_name, phone},
    passengers [{booking_id, employee_id, employee_name, employee_phone, pickup_drop_address, status}]"""


class AssignRequest(BaseModel):
    """TODO: booking_ids: non-empty list of UNIQUE ints"""


class BoardingUpdate(BaseModel):
    """TODO: status: only BOARDED or NO_SHOW"""
