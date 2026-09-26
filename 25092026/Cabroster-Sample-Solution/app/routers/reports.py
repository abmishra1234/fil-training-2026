from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models import Booking, BookingStatus as S, Role, Slot, Trip, TripStatus
from app.schemas import DailySummary, SlotSummary

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_roles(Role.ADMIN))])


@router.get("/daily-summary", response_model=DailySummary, summary="Daily summary")
def daily_summary(travel_date: date, db: Session = Depends(get_db)):
    slots = {}
    for slot in Slot:
        bookings = db.scalars(select(Booking).where(Booking.travel_date == travel_date, Booking.slot == slot)).all()
        trips = db.scalars(select(Trip).where(Trip.travel_date == travel_date, Trip.slot == slot,
                                              Trip.status != TripStatus.CANCELLED)).all()
        count = lambda *st: sum(1 for b in bookings if b.status in st)
        capacity = sum(t.cab.capacity for t in trips)
        boarded = count(S.BOARDED, S.COMPLETED)
        slots[slot] = SlotSummary(
            total_bookings=len(bookings), assigned=count(S.ASSIGNED), unassigned=count(S.BOOKED),
            cancelled=count(S.CANCELLED), boarded=boarded, no_show=count(S.NO_SHOW), trips=len(trips),
            total_capacity=capacity, utilisation_pct=round(boarded * 100 / capacity, 1) if capacity else 0.0,
        )
    return DailySummary(travel_date=travel_date, slots=slots)
