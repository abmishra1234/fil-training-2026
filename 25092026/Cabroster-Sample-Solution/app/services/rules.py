"""Time-based business rules (BR-01, BR-02, BR-04, BR-06, start window)."""
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from app.config import settings
from app.core.deps import IST, to_ist
from app.models import Slot


def departure(travel_date: date, slot: Slot) -> datetime:
    t = settings.PICKUP_TIME if slot == Slot.PICKUP else settings.DROP_TIME
    return datetime.combine(travel_date, t, tzinfo=IST)


def booking_cutoff(travel_date: date, slot: Slot) -> datetime:
    if slot == Slot.PICKUP:
        return datetime.combine(travel_date - timedelta(days=1), settings.PICKUP_BOOKING_CUTOFF, tzinfo=IST)
    return datetime.combine(travel_date, settings.DROP_BOOKING_CUTOFF, tzinfo=IST)


def cancel_cutoff(travel_date: date, slot: Slot) -> datetime:
    return departure(travel_date, slot) - timedelta(minutes=settings.CANCEL_CUTOFF_MINUTES)


def start_window_opens(travel_date: date, slot: Slot) -> datetime:
    return departure(travel_date, slot) - timedelta(minutes=settings.START_WINDOW_MINUTES)


def validate_service_date(travel_date: date, now: datetime) -> None:
    """BR-01 (weekday) and BR-02 (today .. today+7)."""
    today = to_ist(now).date()
    if travel_date.weekday() >= 5:
        raise HTTPException(422, detail="Service runs Monday to Friday only")
    if travel_date < today:
        raise HTTPException(422, detail="Travel date is in the past")
    if travel_date > today + timedelta(days=settings.BOOKING_HORIZON_DAYS):
        raise HTTPException(422, detail=f"Travel date must be within {settings.BOOKING_HORIZON_DAYS} days")
