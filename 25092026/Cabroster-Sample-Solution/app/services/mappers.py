from app.models import Booking, BookingStatus, Trip
from app.schemas import BookingRead, CabRead, DriverBrief, Passenger, TripDetail, TripRead, TripSummary


def seats_booked(trip: Trip) -> int:
    return sum(1 for b in trip.bookings if b.status != BookingStatus.CANCELLED)


def booking_read(b: Booking) -> BookingRead:
    trip = None
    if b.trip is not None:
        trip = TripSummary(
            id=b.trip.id,
            status=b.trip.status,
            cab_registration_no=b.trip.cab.registration_no,
            driver_name=b.trip.driver.full_name,
            driver_phone=b.trip.driver.phone,
        )
    return BookingRead(
        id=b.id, employee_id=b.employee_id, travel_date=b.travel_date, slot=b.slot, zone=b.zone,
        pickup_drop_address=b.pickup_drop_address, status=b.status, trip_id=b.trip_id, trip=trip,
        created_at=b.created_at, cancelled_at=b.cancelled_at,
    )


def trip_read(t: Trip) -> TripRead:
    used = seats_booked(t)
    return TripRead(
        id=t.id, travel_date=t.travel_date, slot=t.slot, zone=t.zone, cab_id=t.cab_id, driver_id=t.driver_id,
        status=t.status, seats_booked=used, seats_available=t.cab.capacity - used,
        started_at=t.started_at, completed_at=t.completed_at, created_at=t.created_at,
    )


def trip_detail(t: Trip) -> TripDetail:
    base = trip_read(t).model_dump()
    return TripDetail(
        **base,
        cab=CabRead.model_validate(t.cab),
        driver=DriverBrief(id=t.driver.id, full_name=t.driver.full_name, phone=t.driver.phone),
        passengers=[
            Passenger(
                booking_id=b.id, employee_id=b.employee_id, employee_name=b.employee.full_name,
                employee_phone=b.employee.phone, pickup_drop_address=b.pickup_drop_address, status=b.status,
            )
            for b in t.bookings if b.status != BookingStatus.CANCELLED
        ],
    )
