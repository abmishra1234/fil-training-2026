"""ORM object -> response schema converters."""
from app.models import Booking, Trip


def seats_booked(trip: Trip) -> int:
    """TODO: number of bookings on the trip that are NOT cancelled."""
    raise NotImplementedError


def booking_read(b: Booking):
    """TODO: build BookingRead, including the nested TripSummary when b.trip is set."""
    raise NotImplementedError


def trip_read(t: Trip):
    """TODO: build TripRead with seats_booked and seats_available = cab.capacity - seats_booked."""
    raise NotImplementedError


def trip_detail(t: Trip):
    """TODO: TripRead + cab + driver + passengers (exclude CANCELLED bookings)."""
    raise NotImplementedError
