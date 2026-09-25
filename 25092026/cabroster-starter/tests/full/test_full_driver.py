"""FULL SUITE — Driver operations (D1–D5, BR-12…BR-15, DEV-14)."""
import pytest

from support import MON, TUE, ids, ist

pytestmark = pytest.mark.full


def _mark(api, trip, drv, booking_id, status):
    return api.patch(f"/driver/trips/{trip['id']}/bookings/{booking_id}", {"status": status}, drv.h)


# ================================================================== D1 / D2
def test_driver_sees_only_own_trips(api):
    """[F-DRV-01] GET /driver/trips | D1, BR-12
    Two drivers, each with trips.
    Expect: each driver lists only their own trips"""
    d1, d2 = api.driver(), api.driver()
    t1 = api.trip(driver_id=d1.id)
    t2 = api.trip(driver_id=d1.id, travel_date=TUE)
    t3 = api.trip(driver_id=d2.id)
    assert set(ids(api.get("/driver/trips", d1.h).json())) == {t1["id"], t2["id"]}
    assert ids(api.get("/driver/trips", d2.h).json()) == [t3["id"]]


def test_driver_trips_default_sort_and_filters(api):
    """[F-DRV-02] GET /driver/trips | D1 default travel_date desc; filters travel_date, status, slot
    Driver has MON PICKUP, MON DROP, TUE PICKUP (cancelled).
    Expect: TUE first; filters return exact sets"""
    d = api.driver()
    mp = api.trip(driver_id=d.id, travel_date=MON, slot="PICKUP")
    md = api.trip(driver_id=d.id, travel_date=MON, slot="DROP")
    tp = api.trip(driver_id=d.id, travel_date=TUE, slot="PICKUP")
    api.patch(f"/trips/{tp['id']}/cancel", None, api.admin.h)
    assert ids(api.get("/driver/trips", d.h).json()) == [tp["id"], mp["id"], md["id"]]
    q = lambda **kw: set(ids(api.get("/driver/trips", d.h, **kw).json()))
    assert q(travel_date=str(MON)) == {mp["id"], md["id"]}
    assert q(status="CANCELLED") == {tp["id"]}
    assert q(slot="DROP") == {md["id"]}


def test_manifest_of_other_driver_is_404(api):
    """[F-DRV-03] GET /driver/trips/{id} | BR-12 (404 not 403)
    Driver B opens driver A's trip; unknown trip.
    Expect: 404 for both"""
    trip, _, _, _ = api.scheduled_trip(passengers=1)
    other = api.driver()
    assert api.get(f"/driver/trips/{trip['id']}", other.h).status_code == 404
    assert api.get("/driver/trips/31337", other.h).status_code == 404


def test_manifest_contents(api):
    """[F-DRV-04] GET /driver/trips/{id} | D2
    Manifest for a trip with 2 passengers.
    Expect: passengers carry employee_name, employee_phone, pickup_drop_address, status ASSIGNED"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=2)
    m = api.get(f"/driver/trips/{trip['id']}", drv.h).json()
    assert len(m["passengers"]) == 2
    for p in m["passengers"]:
        assert {"employee_name", "employee_phone", "pickup_drop_address", "status", "booking_id"} <= p.keys()
        assert p["status"] == "ASSIGNED"


# ================================================================== D3 start
@pytest.mark.parametrize("slot,now,code", [
    ("PICKUP", ist(2026, 9, 28, 5, 59, 59), 422),
    ("PICKUP", ist(2026, 9, 28, 6, 0, 0), 200),
    ("PICKUP", ist(2026, 9, 28, 6, 45), 200),
    ("DROP", ist(2026, 9, 28, 15, 59, 59), 422),
    ("DROP", ist(2026, 9, 28, 16, 0, 0), 200),
    ("PICKUP", ist(2026, 9, 25, 10, 0), 422),
    ("PICKUP", ist(2026, 9, 29, 6, 5), 422),
])
def test_start_window(api, slot, now, code):
    """[F-DRV-05] PATCH /driver/trips/{id}/start | D3 (travel date, from 30 min before departure)
    PICKUP at 05:59:59 / 06:00:00 / 06:45; DROP at 15:59:59 / 16:00:00; PICKUP 3 days early; PICKUP next day.
    Expect: 422 / 200 / 200 / 422 / 200 / 422 / 422"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1, slot=slot)
    api.clock.set(now)
    r = api.patch(f"/driver/trips/{trip['id']}/start", None, drv.h)
    assert r.status_code == code
    expected = "IN_PROGRESS" if code == 200 else "SCHEDULED"
    assert api.trip_detail(trip["id"])["status"] == expected


def test_start_sets_started_at_and_employee_sees_it(api):
    """[F-DRV-06] PATCH /driver/trips/{id}/start | D3
    Start a trip.
    Expect: started_at set; employee's booking trip summary status IN_PROGRESS"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=1)
    r = api.start_trip(trip["id"], drv)
    assert r["status"] == "IN_PROGRESS" and r["started_at"] is not None
    assert api.get(f"/bookings/{bookings[0]['id']}", emps[0].h).json()["trip"]["status"] == "IN_PROGRESS"


def test_start_twice_or_cancelled(api):
    """[F-DRV-07] PATCH /driver/trips/{id}/start | BR-13
    Start an IN_PROGRESS trip again; start a CANCELLED trip.
    Expect: 409 for both"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    assert api.patch(f"/driver/trips/{trip['id']}/start", None, drv.h).status_code == 409
    d2 = api.driver()
    t2 = api.trip(driver_id=d2.id, travel_date=MON, slot="DROP")
    api.patch(f"/trips/{t2['id']}/cancel", None, api.admin.h)
    api.clock.set(ist(2026, 9, 28, 16, 5))
    assert api.patch(f"/driver/trips/{t2['id']}/start", None, d2.h).status_code == 409


def test_start_other_drivers_trip(api):
    """[F-DRV-08] PATCH /driver/trips/{id}/start | BR-12
    Driver B tries to start driver A's trip inside the window.
    Expect: 404 and trip stays SCHEDULED"""
    trip, _, _, _ = api.scheduled_trip(passengers=1)
    other = api.driver()
    api.clock.set(ist(2026, 9, 28, 6, 5))
    assert api.patch(f"/driver/trips/{trip['id']}/start", None, other.h).status_code == 404
    assert api.trip_detail(trip["id"])["status"] == "SCHEDULED"


# ================================================================== D4 boarding
def test_mark_before_start(api):
    """[F-DRV-09] PATCH /driver/trips/{id}/bookings/{bid} | BR-14
    Mark BOARDED while trip is SCHEDULED.
    Expect: 409"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    assert _mark(api, trip, drv, bookings[0]["id"], "BOARDED").status_code == 409


@pytest.mark.parametrize("status", ["CANCELLED", "COMPLETED", "ASSIGNED", "boarded", ""])
def test_mark_invalid_status_value(api, status):
    """[F-DRV-10] PATCH /driver/trips/{id}/bookings/{bid} | D4 (only BOARDED | NO_SHOW)
    Send CANCELLED / COMPLETED / ASSIGNED / lower-case / empty.
    Expect: 422"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    assert _mark(api, trip, drv, bookings[0]["id"], status).status_code == 422


def test_mark_no_show(api):
    """[F-DRV-11] PATCH /driver/trips/{id}/bookings/{bid} | D4
    Mark a passenger NO_SHOW.
    Expect: 200 and booking status NO_SHOW"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    assert _mark(api, trip, drv, bookings[0]["id"], "NO_SHOW").status_code == 200
    assert api.booking(bookings[0]["id"])["status"] == "NO_SHOW"


def test_mark_twice(api):
    """[F-DRV-12] PATCH /driver/trips/{id}/bookings/{bid} | D4 (only ASSIGNED can be marked)
    Mark BOARDED, then BOARDED again, then NO_SHOW.
    Expect: 200, 409, 409; final status BOARDED"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    bid = bookings[0]["id"]
    assert _mark(api, trip, drv, bid, "BOARDED").status_code == 200
    assert _mark(api, trip, drv, bid, "BOARDED").status_code == 409
    assert _mark(api, trip, drv, bid, "NO_SHOW").status_code == 409
    assert api.booking(bid)["status"] == "BOARDED"


def test_mark_booking_not_on_trip(api):
    """[F-DRV-13] PATCH /driver/trips/{id}/bookings/{bid} | D4
    Booking from another trip; unknown booking.
    Expect: 404 for both"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1)
    other_trip, _, _, other_bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    assert _mark(api, trip, drv, other_bookings[0]["id"], "BOARDED").status_code == 404
    assert _mark(api, trip, drv, 60606, "BOARDED").status_code == 404


def test_mark_on_other_drivers_trip(api):
    """[F-DRV-14] PATCH /driver/trips/{id}/bookings/{bid} | BR-12
    Driver B marks a passenger on driver A's in-progress trip.
    Expect: 404 and booking still ASSIGNED"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    other = api.driver()
    assert _mark(api, trip, other, bookings[0]["id"], "BOARDED").status_code == 404
    assert api.booking(bookings[0]["id"])["status"] == "ASSIGNED"


# ================================================================== D5 complete
def test_complete_transitions(api):
    """[F-DRV-15] PATCH /driver/trips/{id}/complete | BR-15
    3 passengers: one BOARDED, one NO_SHOW, one left unmarked; complete.
    Expect: BOARDED->COMPLETED, NO_SHOW stays, unmarked ASSIGNED->NO_SHOW; completed_at set"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=3)
    api.start_trip(trip["id"], drv)
    _mark(api, trip, drv, bookings[0]["id"], "BOARDED")
    _mark(api, trip, drv, bookings[1]["id"], "NO_SHOW")
    r = api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED" and r.json()["completed_at"] is not None
    assert [api.booking(b["id"])["status"] for b in bookings] == ["COMPLETED", "NO_SHOW", "NO_SHOW"]


def test_complete_requires_in_progress(api):
    """[F-DRV-16] PATCH /driver/trips/{id}/complete | BR-13
    Complete a SCHEDULED trip; complete a COMPLETED trip.
    Expect: 409 both times"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1)
    assert api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h).status_code == 409
    api.start_trip(trip["id"], drv)
    assert api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h).status_code == 200
    assert api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h).status_code == 409


def test_complete_other_drivers_trip(api):
    """[F-DRV-17] PATCH /driver/trips/{id}/complete | BR-12
    Driver B completes driver A's in-progress trip.
    Expect: 404 and trip still IN_PROGRESS"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    assert api.patch(f"/driver/trips/{trip['id']}/complete", None, api.driver().h).status_code == 404
    assert api.trip_detail(trip["id"])["status"] == "IN_PROGRESS"


def test_mark_after_complete(api):
    """[F-DRV-18] PATCH /driver/trips/{id}/bookings/{bid} | BR-14
    Try to mark a passenger after the trip is COMPLETED.
    Expect: 409"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert _mark(api, trip, drv, bookings[0]["id"], "BOARDED").status_code == 409


def test_empty_trip_lifecycle(api):
    """[F-DRV-19] start + complete | edge case
    Trip with zero passengers goes through start and complete.
    Expect: 200 for both; final status COMPLETED"""
    trip, drv, _, _ = api.scheduled_trip(passengers=0)
    api.start_trip(trip["id"], drv)
    r = api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"
