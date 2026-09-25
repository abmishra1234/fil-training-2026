"""FULL SUITE — Trips & assignment (T1–T6, BR-07…BR-11, BR-13, BR-16, DEV-12, DEV-13, DEV-15)."""
from datetime import date

import pytest

from support import MON, SAT, SUN, THU_PAST, TUE, ids, ist

pytestmark = pytest.mark.full

TRIP_KEYS = {"id", "travel_date", "slot", "zone", "cab_id", "driver_id", "status", "seats_booked",
             "seats_available", "started_at", "completed_at", "created_at"}


# ================================================================== T1 create
def test_trip_response_shape(api):
    """[F-TRP-01] POST /trips | T1, 4.3
    Create a trip.
    Expect: 201 with every TripRead key; started_at/completed_at null"""
    t = api.trip(capacity=6)
    assert TRIP_KEYS <= t.keys()
    assert t["status"] == "SCHEDULED" and t["seats_available"] == 6 and t["started_at"] is None


@pytest.mark.parametrize("day", [SAT, SUN, THU_PAST, date(2026, 10, 5)])
def test_trip_date_rules(api, day):
    """[F-TRP-02] POST /trips | T1 applies BR-01, BR-02
    Trip on Saturday, Sunday, a past date, and +10 days (now Fri 25-Sep).
    Expect: 422"""
    assert api.trip_resp(api.cab()["id"], api.driver().id, travel_date=day).status_code == 422


def test_trip_unknown_cab_or_driver(api):
    """[F-TRP-03] POST /trips | T1
    Unknown cab id; unknown driver id.
    Expect: 404 for each"""
    assert api.trip_resp(9999, api.driver().id).status_code == 404
    assert api.trip_resp(api.cab()["id"], 9999).status_code == 404


def test_trip_driver_must_be_driver(api):
    """[F-TRP-04] POST /trips | BR-08
    driver_id points to an EMPLOYEE, then to an ADMIN.
    Expect: 422 for both"""
    cab = api.cab()
    assert api.trip_resp(cab["id"], api.employee().id).status_code == 422
    assert api.trip_resp(cab["id"], api.admin.id).status_code == 422


def test_trip_inactive_cab(api):
    """[F-TRP-05] POST /trips | BR-08
    Cab deactivated before trip creation.
    Expect: 422"""
    cab = api.cab()
    api.patch(f"/cabs/{cab['id']}", {"is_active": False}, api.admin.h)
    assert api.trip_resp(cab["id"], api.driver().id).status_code == 422


@pytest.mark.parametrize("body", [{"zone": "MARS"}, {"slot": "NOON"}, {"cab_id": ...}, {"driver_id": ...},
                                  {"travel_date": ...}])
def test_trip_validation(api, body):
    """[F-TRP-06] POST /trips | T1
    Invalid zone / slot, or missing cab_id / driver_id / travel_date.
    Expect: 422"""
    payload = {"travel_date": str(MON), "slot": "PICKUP", "zone": "EAST", "cab_id": api.cab()["id"],
               "driver_id": api.driver().id}
    payload.update(body)
    payload = {k: v for k, v in payload.items() if v is not ...}
    assert api.post("/trips", payload, api.admin.h).status_code == 422


def test_cab_double_booking(api):
    """[F-TRP-07] POST /trips | BR-07 cab
    Same cab, same date+slot, different driver and zone.
    Expect: 409"""
    cab = api.cab()
    api.trip(cab["id"])
    assert api.trip_resp(cab["id"], api.driver().id, zone="WEST").status_code == 409


def test_driver_double_booking(api):
    """[F-TRP-08] POST /trips | BR-07 driver
    Same driver, same date+slot, different cab.
    Expect: 409"""
    d = api.driver()
    api.trip(driver_id=d.id)
    assert api.trip_resp(api.cab()["id"], d.id, zone="WEST").status_code == 409


def test_cab_and_driver_reusable_other_slot_or_date(api):
    """[F-TRP-09] POST /trips | BR-07 scope
    Same cab + driver: MON PICKUP, MON DROP, TUE PICKUP.
    Expect: all 201"""
    cab, d = api.cab(), api.driver()
    for day, slot in [(MON, "PICKUP"), (MON, "DROP"), (TUE, "PICKUP")]:
        assert api.trip_resp(cab["id"], d.id, day, slot).status_code == 201


def test_cancelled_trip_frees_cab_and_driver(api):
    """[F-TRP-10] POST /trips | BR-07 (cancelled trips don't count)
    Create trip, cancel it, create again with same cab and driver.
    Expect: 201"""
    cab, d = api.cab(), api.driver()
    t = api.trip(cab["id"], d.id)
    api.patch(f"/trips/{t['id']}/cancel", None, api.admin.h)
    assert api.trip_resp(cab["id"], d.id).status_code == 201


# ================================================================== T2 / T3
def _trips(api):
    d1, d2 = api.driver(), api.driver()
    c1, c2, c3 = api.cab(4), api.cab(4), api.cab(6)
    t1 = api.trip(c1["id"], d1.id, MON, "PICKUP", "EAST")
    t2 = api.trip(c2["id"], d2.id, MON, "DROP", "WEST")
    t3 = api.trip(c3["id"], d1.id, TUE, "PICKUP", "WEST")
    t4 = api.trip(c1["id"], d2.id, TUE, "DROP", "EAST")
    api.patch(f"/trips/{t4['id']}/cancel", None, api.admin.h)
    return dict(d1=d1, d2=d2, c1=c1, c3=c3, t1=t1, t2=t2, t3=t3, t4=t4)


def test_trip_list_filters(api):
    """[F-TRP-11] GET /trips | T2 filters
    travel_date, date_from/date_to, slot, zone, status, driver_id, cab_id and a combination.
    Expect: exact matching sets"""
    p = _trips(api)
    q = lambda **kw: set(ids(api.get("/trips", api.admin.h, **kw).json()))
    t = {k: p[k]["id"] for k in ("t1", "t2", "t3", "t4")}
    assert q(travel_date=str(MON)) == {t["t1"], t["t2"]}
    assert q(date_from=str(TUE), date_to=str(TUE)) == {t["t3"], t["t4"]}
    assert q(slot="DROP") == {t["t2"], t["t4"]}
    assert q(zone="WEST") == {t["t2"], t["t3"]}
    assert q(status="CANCELLED") == {t["t4"]}
    assert q(driver_id=p["d1"].id) == {t["t1"], t["t3"]}
    assert q(cab_id=p["c1"]["id"]) == {t["t1"], t["t4"]}
    assert q(zone="EAST", status="SCHEDULED") == {t["t1"]}


def test_trip_list_sort(api):
    """[F-TRP-12] GET /trips | T2 sort
    Default (travel_date asc) and travel_date desc.
    Expect: MON trips before TUE trips, and reverse"""
    p = _trips(api)
    asc = ids(api.get("/trips", api.admin.h).json())
    assert asc == [p["t1"]["id"], p["t2"]["id"], p["t3"]["id"], p["t4"]["id"]]
    desc = ids(api.get("/trips", api.admin.h, sort_by="travel_date", order="desc").json())
    assert desc[:2] == [p["t3"]["id"], p["t4"]["id"]]


@pytest.mark.parametrize("params", [{"date_from": str(TUE), "date_to": str(MON)}, {"sort_by": "zone"},
                                    {"status": "DONE"}, {"driver_id": "x"}])
def test_trip_list_invalid_params(api, params):
    """[F-TRP-13] GET /trips | 5.3, 5.4
    Reversed date range, non-whitelisted sort, bad enum, bad int.
    Expect: 422"""
    assert api.get("/trips", api.admin.h, **params).status_code == 422


def test_trip_list_seat_counts(api):
    """[F-TRP-14] GET /trips | T2 seats_booked / seats_available
    6-seat trip with 2 passengers.
    Expect: list item shows seats_booked 2, seats_available 4"""
    trip, *_ = api.scheduled_trip(passengers=2, capacity=6)
    item = api.get("/trips", api.admin.h).json()["items"][0]
    assert item["id"] == trip["id"] and item["seats_booked"] == 2 and item["seats_available"] == 4


def test_trip_detail(api):
    """[F-TRP-15] GET /trips/{id} | T3
    Trip with 2 passengers; unknown id.
    Expect: cab object, driver {id, full_name, phone}, passengers with booking_id/employee_name/employee_phone/pickup_drop_address/status; unknown 404"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=2)
    d = api.trip_detail(trip["id"])
    assert d["cab"]["id"] == trip["cab_id"] and d["driver"]["full_name"] == drv.data["full_name"]
    assert d["driver"]["phone"] == drv.data["phone"]
    assert {p["booking_id"] for p in d["passengers"]} == {b["id"] for b in bookings}
    p0 = next(p for p in d["passengers"] if p["booking_id"] == bookings[0]["id"])
    assert p0["employee_name"] == emps[0].data["full_name"] and p0["employee_phone"] == emps[0].data["phone"]
    assert p0["pickup_drop_address"] == bookings[0]["pickup_drop_address"] and p0["status"] == "ASSIGNED"
    assert api.get("/trips/9999", api.admin.h).status_code == 404


# ================================================================== T4 assign
def test_assign_sets_status_and_trip(api):
    """[F-TRP-16] POST /trips/{id}/bookings | BR-10
    Assign one booking.
    Expect: booking ASSIGNED with trip_id; employee sees trip summary"""
    trip = api.trip()
    e = api.employee()
    b = api.book(e)
    assert api.assign(trip["id"], [b["id"]]).status_code == 200
    mine = api.get(f"/bookings/{b['id']}", e.h).json()
    assert mine["status"] == "ASSIGNED" and mine["trip_id"] == trip["id"] and mine["trip"]["status"] == "SCHEDULED"


@pytest.mark.parametrize("mismatch", ["date", "slot", "zone"])
def test_assign_mismatch(api, mismatch):
    """[F-TRP-17] POST /trips/{id}/bookings | BR-10
    Trip is MON/PICKUP/EAST; booking differs in date (TUE), slot (DROP) or zone (WEST).
    Expect: 409 and booking stays BOOKED"""
    trip = api.trip(travel_date=MON, slot="PICKUP", zone="EAST")
    e = api.employee(zone="WEST" if mismatch == "zone" else "EAST")
    b = api.book(e, TUE if mismatch == "date" else MON, "DROP" if mismatch == "slot" else "PICKUP")
    assert api.assign(trip["id"], [b["id"]]).status_code == 409
    assert api.booking(b["id"])["status"] == "BOOKED"


def test_assign_already_assigned_booking(api):
    """[F-TRP-18] POST /trips/{id}/bookings | BR-10 (status must be BOOKED)
    Booking on trip A is assigned to trip B (same date/slot/zone).
    Expect: 409 and booking still on trip A"""
    trip_a, _, _, bookings = api.scheduled_trip(passengers=1)
    trip_b = api.trip()
    assert api.assign(trip_b["id"], [bookings[0]["id"]]).status_code == 409
    assert api.booking(bookings[0]["id"])["trip_id"] == trip_a["id"]


def test_assign_cancelled_booking(api):
    """[F-TRP-19] POST /trips/{id}/bookings | BR-10
    Assign a CANCELLED booking.
    Expect: 409"""
    trip = api.trip()
    e = api.employee()
    b = api.book(e)
    api.patch(f"/bookings/{b['id']}/cancel", None, e.h)
    assert api.assign(trip["id"], [b["id"]]).status_code == 409


def test_assign_unknown_booking_or_trip(api):
    """[F-TRP-20] POST /trips/{id}/bookings | T4
    Unknown booking id; unknown trip id.
    Expect: 404 for each"""
    trip = api.trip()
    assert api.assign(trip["id"], [8888]).status_code == 404
    b = api.book(api.employee())
    assert api.assign(8888, [b["id"]]).status_code == 404


@pytest.mark.parametrize("payload", [{"booking_ids": []}, {}, {"booking_ids": "1,2"}, "DUP"])
def test_assign_payload_validation(api, payload):
    """[F-TRP-21] POST /trips/{id}/bookings | T4
    Empty list, missing field, wrong type, duplicate ids.
    Expect: 422"""
    trip = api.trip()
    if payload == "DUP":
        b = api.book(api.employee())
        payload = {"booking_ids": [b["id"], b["id"]]}
    assert api.post(f"/trips/{trip['id']}/bookings", payload, api.admin.h).status_code == 422


def test_assign_is_atomic(api):
    """[F-TRP-22] POST /trips/{id}/bookings | T4 all-or-nothing
    Assign [valid, valid, wrong-zone].
    Expect: 409 and the two valid bookings remain BOOKED with trip_id null; trip seats_booked 0"""
    trip = api.trip()
    good = [api.book(api.employee())["id"] for _ in range(2)]
    bad = api.book(api.employee(zone="WEST"))["id"]
    assert api.assign(trip["id"], good + [bad]).status_code == 409
    for bid in good:
        b = api.booking(bid)
        assert b["status"] == "BOOKED" and b["trip_id"] is None
    assert api.trip_detail(trip["id"])["seats_booked"] == 0


def test_capacity_exact_fill_then_overflow(api):
    """[F-TRP-23] POST /trips/{id}/bookings | BR-09
    4-seat cab: assign 4 (exact) then 1 more.
    Expect: 200 with seats_available 0; then 409"""
    trip = api.trip(capacity=4)
    four = [api.book(api.employee())["id"] for _ in range(4)]
    r = api.assign(trip["id"], four)
    assert r.status_code == 200 and r.json()["seats_available"] == 0
    assert api.assign(trip["id"], [api.book(api.employee())["id"]]).status_code == 409


def test_capacity_incremental(api):
    """[F-TRP-24] POST /trips/{id}/bookings | BR-09 (counts seats already taken)
    4-seat cab: assign 2, then assign 3 more.
    Expect: 200 then 409; none of the 3 assigned (still BOOKED)"""
    trip = api.trip(capacity=4)
    assert api.assign(trip["id"], [api.book(api.employee())["id"] for _ in range(2)]).status_code == 200
    three = [api.book(api.employee())["id"] for _ in range(3)]
    assert api.assign(trip["id"], three).status_code == 409
    assert all(api.booking(b)["status"] == "BOOKED" for b in three)
    assert api.trip_detail(trip["id"])["seats_booked"] == 2


@pytest.mark.parametrize("state", ["CANCELLED", "IN_PROGRESS", "COMPLETED"])
def test_assign_to_non_scheduled_trip(api, state):
    """[F-TRP-25] POST /trips/{id}/bookings | BR-11
    Trip CANCELLED / IN_PROGRESS / COMPLETED; assign a matching BOOKED booking.
    Expect: 409"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1, capacity=4)
    spare = api.book(api.employee())  # matching MON/PICKUP/EAST booking, still BOOKED
    if state == "CANCELLED":
        api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h)
    else:
        api.start_trip(trip["id"], drv)
        if state == "COMPLETED":
            api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert api.assign(trip["id"], [spare["id"]]).status_code == 409
    assert api.booking(spare["id"])["status"] == "BOOKED"


# ================================================================== T5 remove
def test_remove_then_reassign_elsewhere(api):
    """[F-TRP-26] DELETE /trips/{id}/bookings/{booking_id} | T5
    Remove booking from trip A, assign it to trip B.
    Expect: remove 200/204 (seats_booked on A drops); assign to B 200"""
    trip_a, _, _, bookings = api.scheduled_trip(passengers=2)
    bid = bookings[0]["id"]
    r = api.delete(f"/trips/{trip_a['id']}/bookings/{bid}", api.admin.h)
    assert r.status_code in (200, 204)
    assert api.trip_detail(trip_a["id"])["seats_booked"] == 1
    trip_b = api.trip()
    assert api.assign(trip_b["id"], [bid]).status_code == 200


def test_remove_booking_not_on_trip(api):
    """[F-TRP-27] DELETE /trips/{id}/bookings/{booking_id} | T5
    Booking that belongs to another trip; unassigned booking; unknown booking; unknown trip.
    Expect: 404 each"""
    trip_a, _, _, a_bookings = api.scheduled_trip(passengers=1)
    trip_b = api.trip()
    loose = api.book(api.employee())
    assert api.delete(f"/trips/{trip_b['id']}/bookings/{a_bookings[0]['id']}", api.admin.h).status_code == 404
    assert api.delete(f"/trips/{trip_b['id']}/bookings/{loose['id']}", api.admin.h).status_code == 404
    assert api.delete(f"/trips/{trip_b['id']}/bookings/7777", api.admin.h).status_code == 404
    assert api.delete(f"/trips/7777/bookings/{a_bookings[0]['id']}", api.admin.h).status_code == 404


def test_remove_from_started_trip(api):
    """[F-TRP-28] DELETE /trips/{id}/bookings/{booking_id} | BR-11
    Trip IN_PROGRESS; remove a passenger.
    Expect: 409 and passenger still ASSIGNED"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    assert api.delete(f"/trips/{trip['id']}/bookings/{bookings[0]['id']}", api.admin.h).status_code == 409
    assert api.booking(bookings[0]["id"])["status"] == "ASSIGNED"


# ================================================================== T6 cancel
def test_cancel_trip_releases_bookings(api):
    """[F-TRP-29] PATCH /trips/{id}/cancel | BR-16
    Trip with 3 passengers is cancelled.
    Expect: trip CANCELLED; all 3 bookings BOOKED with trip_id null; they appear in unassigned=true"""
    trip, _, _, bookings = api.scheduled_trip(passengers=3)
    assert api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h).json()["status"] == "CANCELLED"
    for b in bookings:
        got = api.booking(b["id"])
        assert got["status"] == "BOOKED" and got["trip_id"] is None
    un = set(ids(api.get("/bookings", api.admin.h, unassigned="true").json()))
    assert {b["id"] for b in bookings} <= un


def test_cancelled_booking_stays_cancelled_when_trip_cancelled(api):
    """[F-TRP-30] PATCH /trips/{id}/cancel | BR-16 (only active bookings go back)
    Passenger cancels, then admin cancels the trip.
    Expect: that booking remains CANCELLED"""
    trip, _, emps, bookings = api.scheduled_trip(passengers=2)
    api.patch(f"/bookings/{bookings[0]['id']}/cancel", None, emps[0].h)
    api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h)
    assert api.booking(bookings[0]["id"])["status"] == "CANCELLED"
    assert api.booking(bookings[1]["id"])["status"] == "BOOKED"


@pytest.mark.parametrize("state", ["CANCELLED", "IN_PROGRESS", "COMPLETED"])
def test_cancel_trip_invalid_state(api, state):
    """[F-TRP-31] PATCH /trips/{id}/cancel | BR-13
    Cancel a trip that is already CANCELLED / IN_PROGRESS / COMPLETED.
    Expect: 409"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1)
    if state == "CANCELLED":
        api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h)
    else:
        api.start_trip(trip["id"], drv)
        if state == "COMPLETED":
            api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h).status_code == 409


def test_cancel_unknown_trip(api):
    """[F-TRP-32] PATCH /trips/{id}/cancel | T6
    Unknown id.
    Expect: 404"""
    assert api.patch("/trips/4040/cancel", None, api.admin.h).status_code == 404


def test_passenger_list_excludes_cancelled(api):
    """[F-TRP-33] GET /trips/{id} | T3, BR-06
    3 passengers, one cancels.
    Expect: passengers list has 2 and seats_booked 2"""
    trip, _, emps, bookings = api.scheduled_trip(passengers=3)
    api.patch(f"/bookings/{bookings[1]['id']}/cancel", None, emps[1].h)
    d = api.trip_detail(trip["id"])
    assert len(d["passengers"]) == 2 and d["seats_booked"] == 2
    assert bookings[1]["id"] not in {p["booking_id"] for p in d["passengers"]}
