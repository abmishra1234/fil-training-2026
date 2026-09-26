import re
from datetime import date, datetime
from typing import Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import BookingStatus, Role, Slot, TripStatus, Zone

T = TypeVar("T")
PHONE = r"^[6-9]\d{9}$"
REG_NO = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- users / auth ----------
def _check_password(v: str) -> str:
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Password must contain at least one letter and one digit")
    return v


class _UserBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(pattern=PHONE)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("full_name must be at least 2 characters")
        return v

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return _check_password(v)


class UserRegister(_UserBase):
    employee_code: str = Field(min_length=1, max_length=20)
    home_address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    zone: Optional[Zone] = None


class UserCreateByAdmin(_UserBase):
    role: Literal[Role.DRIVER, Role.ADMIN]
    license_no: Optional[str] = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode="after")
    def _driver_license(self):
        if self.role == Role.DRIVER and not self.license_no:
            raise ValueError("license_no is required for DRIVER")
        return self


class UserRead(ORM):
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


class ProfileUpdate(BaseModel):
    phone: Optional[str] = Field(default=None, pattern=PHONE)
    home_address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    zone: Optional[Zone] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


# ---------- cabs ----------
class CabCreate(BaseModel):
    registration_no: str
    model: str = Field(min_length=1, max_length=50)
    capacity: int = Field(ge=1, le=12)

    @field_validator("registration_no")
    @classmethod
    def _reg(cls, v: str) -> str:
        v = v.strip().upper()
        if not REG_NO.match(v):
            raise ValueError("Invalid registration number")
        return v


class CabUpdate(BaseModel):
    model: Optional[str] = Field(default=None, min_length=1, max_length=50)
    capacity: Optional[int] = Field(default=None, ge=1, le=12)
    is_active: Optional[bool] = None


class CabRead(ORM):
    id: int
    registration_no: str
    model: str
    capacity: int
    is_active: bool
    created_at: datetime


# ---------- bookings ----------
class BookingCreate(BaseModel):
    travel_date: date
    slot: Slot


class TripSummary(BaseModel):
    id: int
    status: TripStatus
    cab_registration_no: str
    driver_name: str
    driver_phone: str


class BookingRead(BaseModel):
    id: int
    employee_id: int
    travel_date: date
    slot: Slot
    zone: Zone
    pickup_drop_address: str
    status: BookingStatus
    trip_id: Optional[int]
    trip: Optional[TripSummary]
    created_at: datetime
    cancelled_at: Optional[datetime]


# ---------- trips ----------
class TripCreate(BaseModel):
    travel_date: date
    slot: Slot
    zone: Zone
    cab_id: int
    driver_id: int


class TripRead(BaseModel):
    id: int
    travel_date: date
    slot: Slot
    zone: Zone
    cab_id: int
    driver_id: int
    status: TripStatus
    seats_booked: int
    seats_available: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class DriverBrief(BaseModel):
    id: int
    full_name: str
    phone: str


class Passenger(BaseModel):
    booking_id: int
    employee_id: int
    employee_name: str
    employee_phone: str
    pickup_drop_address: str
    status: BookingStatus


class TripDetail(TripRead):
    cab: CabRead
    driver: DriverBrief
    passengers: List[Passenger]


class AssignRequest(BaseModel):
    booking_ids: List[int] = Field(min_length=1)

    @field_validator("booking_ids")
    @classmethod
    def _unique(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("booking_ids must be unique")
        return v


class BoardingUpdate(BaseModel):
    status: Literal[BookingStatus.BOARDED, BookingStatus.NO_SHOW]


# ---------- reports ----------
class SlotSummary(BaseModel):
    total_bookings: int
    assigned: int
    unassigned: int
    cancelled: int
    boarded: int
    no_show: int
    trips: int
    total_capacity: int
    utilisation_pct: float


class DailySummary(BaseModel):
    travel_date: date
    slots: dict[Slot, SlotSummary]
