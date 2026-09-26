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

    bookings: Mapped[list["Booking"]] = relationship(back_populates="employee")


class Cab(Base):
    __tablename__ = "cabs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registration_no: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(50))
    capacity: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    travel_date: Mapped[date] = mapped_column(Date, index=True)
    slot: Mapped[Slot] = mapped_column(Enum(Slot))
    zone: Mapped[Zone] = mapped_column(Enum(Zone))
    cab_id: Mapped[int] = mapped_column(ForeignKey("cabs.id"))
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[TripStatus] = mapped_column(Enum(TripStatus), default=TripStatus.SCHEDULED)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cab: Mapped[Cab] = relationship()
    driver: Mapped[User] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(back_populates="trip", order_by="Booking.id")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    travel_date: Mapped[date] = mapped_column(Date, index=True)
    slot: Mapped[Slot] = mapped_column(Enum(Slot))
    zone: Mapped[Zone] = mapped_column(Enum(Zone))
    pickup_drop_address: Mapped[str] = mapped_column(String(255))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.BOOKED)
    trip_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trips.id"), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee: Mapped[User] = relationship(back_populates="bookings")
    trip: Mapped[Optional[Trip]] = relationship(back_populates="bookings")
