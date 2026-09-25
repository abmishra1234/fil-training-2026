"""SQLAlchemy models (DEV-02).

DONE for you : all enums + the User model (use it as the pattern).
YOUR TASK    : complete Cab, Trip and Booking exactly as in spec section 4.
Do NOT rename User / Role or their columns — the tests insert the first ADMIN directly.
"""
import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"
    DRIVER = "DRIVER"


class Zone(str, enum.Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"
    CENTRAL = "CENTRAL"


class Slot(str, enum.Enum):
    PICKUP = "PICKUP"
    DROP = "DROP"


class BookingStatus(str, enum.Enum):
    BOOKED = "BOOKED"
    ASSIGNED = "ASSIGNED"
    BOARDED = "BOARDED"
    NO_SHOW = "NO_SHOW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TripStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(15))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.EMPLOYEE)
    employee_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    home_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    zone: Mapped[Optional[Zone]] = mapped_column(Enum(Zone), nullable=True)
    license_no: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # TODO (DEV-02): relationship to Booking, e.g.
    # bookings: Mapped[list["Booking"]] = relationship(back_populates="employee")


class Cab(Base):
    __tablename__ = "cabs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # TODO (DEV-02): registration_no (unique), model, capacity, is_active, created_at  -> spec 4.2


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # TODO (DEV-02): travel_date, slot, zone, cab_id (FK), driver_id (FK), status, started_at,
    #                completed_at, created_at  -> spec 4.3
    # TODO: relationships cab, driver, bookings


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # TODO (DEV-02): employee_id (FK), travel_date, slot, zone, pickup_drop_address, status,
    #                trip_id (nullable FK), cancelled_at, created_at  -> spec 4.4
    # TODO: relationships employee, trip
