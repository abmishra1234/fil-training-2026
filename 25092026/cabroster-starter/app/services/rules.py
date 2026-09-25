"""Time-based business rules. Pure functions — easy to unit test.

Hint: build IST datetimes with datetime.combine(d, t, tzinfo=IST) and compare with to_ist(now).
"""
from datetime import date, datetime, timedelta  # noqa: F401

from fastapi import HTTPException  # noqa: F401

from app.config import settings  # noqa: F401
from app.core.deps import IST, to_ist  # noqa: F401
from app.models import Slot


def departure(travel_date: date, slot: Slot) -> datetime:
    """TODO: 06:30 (PICKUP) or 16:30 (DROP) on travel_date, IST."""
    raise NotImplementedError


def booking_cutoff(travel_date: date, slot: Slot) -> datetime:
    """TODO (BR-04): PICKUP -> 21:00 on the previous day; DROP -> 14:00 same day."""
    raise NotImplementedError


def cancel_cutoff(travel_date: date, slot: Slot) -> datetime:
    """TODO (BR-06): departure - 60 minutes."""
    raise NotImplementedError


def start_window_opens(travel_date: date, slot: Slot) -> datetime:
    """TODO (D3): departure - 30 minutes."""
    raise NotImplementedError


def validate_service_date(travel_date: date, now: datetime) -> None:
    """TODO (BR-01, BR-02): weekend -> 422; past -> 422; later than today+7 -> 422."""
    raise NotImplementedError
