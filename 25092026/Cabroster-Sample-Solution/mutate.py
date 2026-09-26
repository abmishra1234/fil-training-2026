"""Inject one bug at a time into the reference app and check the suites catch it."""
import os
import subprocess
import sys

M = [
    ("BR-03 cancelled blocks rebooking", "app/services/booking_service.py",
     "Booking.slot == data.slot, Booking.status != BookingStatus.CANCELLED))", "Booking.slot == data.slot))"),
    ("BR-04 cut-off off-by-one", "app/services/booking_service.py",
     "if to_ist(now) >= rules.booking_cutoff", "if to_ist(now) > rules.booking_cutoff"),
    ("BR-06 cancel cut-off off-by-one", "app/services/booking_service.py",
     "to_ist(now) >= rules.cancel_cutoff", "to_ist(now) > rules.cancel_cutoff"),
    ("BR-06 seat not freed", "app/services/booking_service.py", "    b.trip_id = None\n", ""),
    ("BR-06 admin bound by cut-off", "app/services/booking_service.py",
     "if user.role == Role.EMPLOYEE and to_ist(now)", "if to_ist(now)"),
    ("B3 ownership missing", "app/services/booking_service.py",
     "(user.role == Role.EMPLOYEE and b.employee_id != user.id)", "False"),
    ("BR-05 zone not checked", "app/services/booking_service.py",
     "if not user.home_address or not user.zone:", "if not user.home_address:"),
    ("BR-01 weekend allowed", "app/services/rules.py", "travel_date.weekday() >= 5", "travel_date.weekday() >= 6"),
    ("BR-02 horizon off-by-one", "app/services/rules.py",
     "if travel_date > today + timedelta", "if travel_date >= today + timedelta"),
    ("BR-02 past allowed", "app/services/rules.py", "if travel_date < today:", "if False:"),
    ("Start window off-by-one", "app/services/trip_service.py",
     "or now < rules.start_window_opens", "or now <= rules.start_window_opens"),
    ("Start allowed any day", "app/services/trip_service.py", "if now.date() != trip.travel_date or now <",
     "if now <"),
    ("BR-09 capacity off-by-one", "app/services/trip_service.py",
     "if used + len(bookings) > trip.cab.capacity", "if used + len(bookings) >= trip.cab.capacity + 1 + 0 and False"),
    ("BR-09 ignores seats already used", "app/services/trip_service.py",
     "if used + len(bookings) > trip.cab.capacity", "if len(bookings) > trip.cab.capacity"),
    ("BR-10 zone not checked", "app/services/trip_service.py",
     "(b.travel_date, b.slot, b.zone) != (trip.travel_date, trip.slot, trip.zone)",
     "(b.travel_date, b.slot) != (trip.travel_date, trip.slot)"),
    ("BR-10 status not checked", "app/services/trip_service.py", "if b.status != BookingStatus.BOOKED:", "if False:"),
    ("T4 not atomic", "app/services/trip_service.py",
     "        bookings.append(b)\n",
     "        bookings.append(b)\n        b.trip_id = trip.id; b.status = BookingStatus.ASSIGNED; db.commit()\n"),
    ("BR-11 assign to started trip", "app/services/trip_service.py",
     "    if trip.status != TripStatus.SCHEDULED:                                 # BR-11", "    if False:"),
    ("BR-07 cancelled trips block", "app/services/trip_service.py",
     "Trip.status != TripStatus.CANCELLED)) is not None", "True) is not None"),
    ("BR-07 driver clash unchecked", "app/services/trip_service.py",
     "if _busy(db, Trip.driver_id, driver.id", "if False and _busy(db, Trip.driver_id, driver.id"),
    ("BR-08 driver role unchecked", "app/services/trip_service.py",
     "if driver.role != Role.DRIVER or not driver.is_active:", "if not driver.is_active:"),
    ("BR-12 driver ownership missing", "app/services/trip_service.py",
     "if t is None or t.driver_id != driver.id:", "if t is None:"),
    ("BR-14 mark before start", "app/services/trip_service.py",
     "    if trip.status != TripStatus.IN_PROGRESS:                               # BR-14", "    if False:"),
    ("BR-14 re-mark allowed", "app/services/trip_service.py",
     "if b.status != BookingStatus.ASSIGNED:", "if b.status not in (BookingStatus.ASSIGNED, BookingStatus.BOARDED):"),
    ("BR-15 no-show not applied", "app/services/trip_service.py",
     "            b.status = BookingStatus.NO_SHOW\n", "            pass\n"),
    ("BR-16 bookings not released", "app/services/trip_service.py",
     "            b.status = BookingStatus.BOOKED\n            b.trip_id = None\n", "            pass\n"),
    ("BR-16 cancelled bookings revived", "app/services/trip_service.py",
     "        if b.status != BookingStatus.CANCELLED:\n            b.status = BookingStatus.BOOKED",
     "        if True:\n            b.status = BookingStatus.BOOKED"),
    ("BR-13 cancel in-progress trip", "app/services/trip_service.py",
     "    if trip.status != TripStatus.SCHEDULED:                                 # BR-13", "    if False:"),
    ("T5 remove from started trip", "app/services/trip_service.py",
     "raise HTTPException(404, detail=\"Booking not found on this trip\")\n    if trip.status != TripStatus.SCHEDULED:",
     "raise HTTPException(404, detail=\"Booking not found on this trip\")\n    if False:"),
    ("seats count cancelled", "app/services/mappers.py",
     "return sum(1 for b in trip.bookings if b.status != BookingStatus.CANCELLED)", "return len(trip.bookings)"),
    ("inactive user token accepted", "app/core/deps.py", "if user is None or not user.is_active:", "if user is None:"),
    ("role trusted from token", "app/core/deps.py", "if user.role not in roles:",
     "if user.role not in roles and False:"),
    ("pages uses floor", "app/core/query.py", "math.ceil(total / size)", "total // size"),
    ("total ignores filters", "app/core/query.py",
     "select(func.count()).select_from(stmt.order_by(None).subquery())", "select(func.count()).select_from(stmt.froms[0])"),
    ("sort tie-break missing / desc ignored", "app/core/query.py",
     "col.desc() if order == \"desc\" else col.asc()", "col.asc()"),
    ("email not lower-cased", "app/schemas.py", "        return v.lower()", "        return v"),
    ("password rule missing", "app/schemas.py",
     "    if not re.search(r\"[A-Za-z]\", v) or not re.search(r\"\\d\", v):", "    if False:"),
    ("phone regex loose", "app/schemas.py", 'PHONE = r"^[6-9]\\d{9}$"', 'PHONE = r"^\\d{10}$"'),
    ("duplicate booking_ids allowed", "app/schemas.py", "if len(set(v)) != len(v):", "if False:"),
    ("driver may edit address", "app/routers/auth.py",
     "if user.role == Role.DRIVER and", "if False and"),
    ("login case-sensitive", "app/routers/auth.py", "form.username.strip().lower()", "form.username"),
    ("cab capacity shrink unchecked", "app/routers/cabs.py",
     "if any(seats_booked(t) > changes[\"capacity\"] for t in trips):", "if False:"),
    ("available_on ignores cancelled status", "app/routers/cabs.py",
     "Trip.status != TripStatus.CANCELLED)\n        stmt = stmt.where(Cab.is_active.is_(True)",
     "True)\n        stmt = stmt.where(Cab.is_active.is_(True)"),
    ("unassigned filter wrong", "app/routers/bookings.py",
     "cond = and_(Booking.trip_id.is_(None), Booking.status == BookingStatus.BOOKED)",
     "cond = Booking.trip_id.is_(None)"),
    ("my bookings default asc", "app/routers/bookings.py",
     'sort_by: Literal["travel_date", "created_at"] = "travel_date",\n    order: Literal["asc", "desc"] = "desc",',
     'sort_by: Literal["travel_date", "created_at"] = "travel_date",\n    order: Literal["asc", "desc"] = "asc",'),
    ("admin list open to employees", "app/routers/bookings.py",
     "pg: PageParams = Depends(), _=Depends(admin_only)", "pg: PageParams = Depends(), _=Depends(employee_or_admin)"),
    ("self-deactivation allowed", "app/routers/users.py", "if user.id == me.id:", "if False:"),
    ("date range not validated", "app/core/query.py", "if date_from and date_to and date_from > date_to:", "if False:"),
]

SUITE = sys.argv[1] if len(sys.argv) > 1 else "tests/full"
env = dict(os.environ, BCRYPT_ROUNDS="4")
survivors = []
for name, path, old, new in M:
    src = open(path).read()
    if src.count(old) != 1:
        print(f"!! pattern not unique/found for: {name} ({src.count(old)})")
        continue
    open(path, "w").write(src.replace(old, new))
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", SUITE, "-x", "-q", "-W", "ignore", "-m", "not stretch",
                            "-p", "no:randomly"], capture_output=True, text=True, env=env, timeout=900)
        caught = r.returncode != 0
    finally:
        open(path, "w").write(src)
    print(("CAUGHT   " if caught else "SURVIVED ") + name, flush=True)
    if not caught:
        survivors.append(name)
print(f"\n{len(M) - len(survivors)}/{len(M)} mutants caught by {SUITE}")
