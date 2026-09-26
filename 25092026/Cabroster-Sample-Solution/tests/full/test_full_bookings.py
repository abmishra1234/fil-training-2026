"""FULL SUITE — Bookings (B1–B5, BR-01…BR-06, DEV-09…DEV-11).

Default fake time: Fri 25-Sep-2026 10:00 IST.
"""
from datetime import date

import pytest

from support import FRI, MON, SAT, SUN, THU_PAST, TUE, WED, ids, ist

pytestmark = pytest.mark.full

BOOKING_KEYS = {"id", "employee_id", "travel_date", "slot", "zone", "pickup_drop_address", "status",
                "trip_id", "trip", "created_at", "cancelled_at"}


# ================================================================== B1 create
def test_booking_response_shape(api):
    """[F-BKG-01] POST /bookings | B1, 4.4
    Create a booking and inspect it.
    Expect: all BookingRead keys; status BOOKED; trip_id/trip/cancelled_at null"""
    b = api.book(api.employee())
    assert BOOKING_KEYS <= b.keys()
    assert b["status"] == "BOOKED" and b["trip_id"] is None and b["trip"] is None and b["cancelled_at"] is None
    assert b["travel_date"] == str(MON) and b["slot"] == "PICKUP"


@pytest.mark.parametrize("day", [SAT, SUN])
def test_weekend_rejected(api, day):
    """[F-BKG-02] POST /bookings | BR-01
    Book PICKUP and DROP on Saturday / Sunday.
    Expect: 422 for both slots"""
    e = api.employee()
    assert api.book_resp(e, day, "PICKUP").status_code == 422
    assert api.book_resp(e, day, "DROP").status_code == 422


def test_past_date_rejected(api):
    """[F-BKG-03] POST /bookings | BR-02
    Book DROP for yesterday (Thu 24-Sep).
    Expect: 422"""
    assert api.book_resp(api.employee(), THU_PAST, "DROP").status_code == 422


def test_booking_horizon_seven_days(api):
    """[F-BKG-04] POST /bookings | BR-02 (today .. today+7 inclusive)
    Now Mon 28-Sep 10:00. Book Mon 05-Oct (+7) and Tue 06-Oct (+8).
    Expect: +7 -> 201; +8 -> 422"""
    api.clock.set(ist(2026, 9, 28, 10, 0))
    e = api.employee()
    assert api.book_resp(e, date(2026, 10, 5), "PICKUP").status_code == 201
    assert api.book_resp(e, date(2026, 10, 6), "PICKUP").status_code == 422


def test_same_day_booking(api):
    """[F-BKG-05] POST /bookings | BR-02, BR-04
    Now Fri 10:00. Book today's DROP and today's PICKUP.
    Expect: DROP 201 (before 14:00); PICKUP 422 (cut-off was 21:00 yesterday)"""
    e = api.employee()
    assert api.book_resp(e, FRI, "DROP").status_code == 201
    assert api.book_resp(e, FRI, "PICKUP").status_code == 422


@pytest.mark.parametrize("now,code", [
    (ist(2026, 9, 28, 20, 59, 59), 201),
    (ist(2026, 9, 28, 21, 0, 0), 422),
    (ist(2026, 9, 28, 23, 30), 422),
])
def test_pickup_cutoff_boundary(api, now, code):
    """[F-BKG-06] POST /bookings | BR-04 PICKUP cut-off 21:00 previous day
    Book Tue PICKUP at Mon 20:59:59 / 21:00:00 / 23:30.
    Expect: 201 / 422 / 422"""
    api.clock.set(now)
    assert api.book_resp(api.employee(), TUE, "PICKUP").status_code == code


def test_pickup_cutoff_for_monday_is_sunday_night(api):
    """[F-BKG-07] POST /bookings | BR-04 (previous CALENDAR day, even if weekend)
    Book Mon PICKUP at Sun 20:59 and at Sun 21:00.
    Expect: 201 then 422"""
    api.clock.set(ist(2026, 9, 27, 20, 59))
    assert api.book_resp(api.employee(), MON, "PICKUP").status_code == 201
    api.clock.set(ist(2026, 9, 27, 21, 0))
    assert api.book_resp(api.employee(), MON, "PICKUP").status_code == 422


@pytest.mark.parametrize("now,code", [
    (ist(2026, 9, 28, 13, 59, 59), 201),
    (ist(2026, 9, 28, 14, 0, 0), 422),
    (ist(2026, 9, 28, 16, 45), 422),
])
def test_drop_cutoff_boundary(api, now, code):
    """[F-BKG-08] POST /bookings | BR-04 DROP cut-off 14:00 same day
    Book Mon DROP at Mon 13:59:59 / 14:00:00 / 16:45.
    Expect: 201 / 422 / 422"""
    api.clock.set(now)
    assert api.book_resp(api.employee(), MON, "DROP").status_code == code


def test_drop_for_tomorrow_after_todays_cutoff(api):
    """[F-BKG-09] POST /bookings | BR-04
    At Mon 15:00 book Tue DROP (Mon's 14:00 cut-off must not apply).
    Expect: 201"""
    api.clock.set(ist(2026, 9, 28, 15, 0))
    assert api.book_resp(api.employee(), TUE, "DROP").status_code == 201


@pytest.mark.parametrize("missing", ["home_address", "zone", "both"])
def test_incomplete_profile(api, missing):
    """[F-BKG-10] POST /bookings | BR-05
    Employee registered without address / zone / both tries to book; then completes profile and retries.
    Expect: 422 first; 201 after PATCH /auth/me"""
    overrides = {"home_address": ..., "zone": ...} if missing == "both" else {missing: ...}
    e = api.employee(**overrides)
    assert api.book_resp(e).status_code == 422
    api.patch("/auth/me", {"home_address": "7 Church St", "zone": "CENTRAL"}, e.h)
    assert api.book_resp(e).status_code == 201


def test_duplicate_blocked_but_cancelled_does_not_block(api):
    """[F-BKG-11] POST /bookings | BR-03
    Book, book again (dup), cancel the first, book again.
    Expect: 201, 409, 200, 201"""
    e = api.employee()
    first = api.book(e)
    assert api.book_resp(e).status_code == 409
    assert api.patch(f"/bookings/{first['id']}/cancel", None, e.h).status_code == 200
    assert api.book_resp(e).status_code == 201


def test_duplicate_while_assigned(api):
    """[F-BKG-12] POST /bookings | BR-03 (ASSIGNED is still active)
    Booking already ASSIGNED to a trip; employee books same date/slot again.
    Expect: 409"""
    trip, _, emps, _ = api.scheduled_trip(passengers=1)
    assert api.book_resp(emps[0]).status_code == 409


def test_duplicate_scope(api):
    """[F-BKG-13] POST /bookings | BR-03 scope = (employee, date, slot)
    Same employee: MON PICKUP + MON DROP + TUE PICKUP; another employee MON PICKUP.
    Expect: all 201"""
    e1, e2 = api.employee(), api.employee()
    for who, d, s in [(e1, MON, "PICKUP"), (e1, MON, "DROP"), (e1, TUE, "PICKUP"), (e2, MON, "PICKUP")]:
        assert api.book_resp(who, d, s).status_code == 201


@pytest.mark.parametrize("body", [{"travel_date": "2026-09-28", "slot": "LUNCH"},
                                  {"travel_date": "28-09-2026", "slot": "PICKUP"},
                                  {"travel_date": "2026-02-30", "slot": "PICKUP"},
                                  {"slot": "PICKUP"}, {"travel_date": "2026-09-28"}, {}])
def test_booking_validation(api, body):
    """[F-BKG-14] POST /bookings | B1
    Bad slot, wrong date format, impossible date, missing fields, empty body.
    Expect: 422"""
    assert api.post("/bookings", body, api.employee().h).status_code == 422


def test_booking_snapshots_address_and_zone(api):
    """[F-BKG-15] POST /bookings | 4.4, Assumption 7
    Book, then change profile address and zone.
    Expect: existing booking keeps original address/zone; a new booking uses the new ones"""
    e = api.employee(home_address="Old Street", zone="EAST")
    b = api.book(e, MON)
    api.patch("/auth/me", {"home_address": "New Street", "zone": "WEST"}, e.h)
    old = api.get(f"/bookings/{b['id']}", e.h).json()
    assert old["pickup_drop_address"] == "Old Street" and old["zone"] == "EAST"
    new = api.book(e, TUE)
    assert new["pickup_drop_address"] == "New Street" and new["zone"] == "WEST"


def test_deactivated_employee_cannot_book(api):
    """[F-BKG-16] POST /bookings | BR-17
    Employee deactivated after login tries to book.
    Expect: 401"""
    e = api.employee()
    api.patch(f"/users/{e.id}/status", {"is_active": False}, api.admin.h)
    assert api.book_resp(e).status_code == 401


# ================================================================== B2 my bookings
def _history(api):
    e = api.employee()
    other = api.employee()
    b_mon_p = api.book(e, MON, "PICKUP")
    b_mon_d = api.book(e, MON, "DROP")
    b_wed_p = api.book(e, WED, "PICKUP")
    b_tue_d = api.book(e, TUE, "DROP")
    api.patch(f"/bookings/{b_tue_d['id']}/cancel", None, e.h)
    api.book(other, MON, "PICKUP")
    return e, dict(mon_p=b_mon_p, mon_d=b_mon_d, wed_p=b_wed_p, tue_d=b_tue_d)


def test_my_bookings_only_own(api):
    """[F-BKG-17] GET /bookings/me | B2, ownership
    Two employees have bookings.
    Expect: each sees only their own; total counts only own"""
    e, b = _history(api)
    r = api.get("/bookings/me", e.h).json()
    assert r["total"] == 4 and all(x["employee_id"] == e.id for x in r["items"])


def test_my_bookings_default_sort_travel_date_desc(api):
    """[F-BKG-18] GET /bookings/me | B2 default travel_date desc (ties by id asc)
    List without params.
    Expect: WED, TUE, MON-PICKUP, MON-DROP"""
    e, b = _history(api)
    assert ids(api.get("/bookings/me", e.h).json()) == [b["wed_p"]["id"], b["tue_d"]["id"], b["mon_p"]["id"],
                                                        b["mon_d"]["id"]]


def test_my_bookings_sort_asc(api):
    """[F-BKG-19] GET /bookings/me | B2 sort
    sort_by=travel_date&order=asc.
    Expect: MON-PICKUP, MON-DROP, TUE, WED"""
    e, b = _history(api)
    r = api.get("/bookings/me", e.h, sort_by="travel_date", order="asc").json()
    assert ids(r) == [b["mon_p"]["id"], b["mon_d"]["id"], b["tue_d"]["id"], b["wed_p"]["id"]]


def test_my_bookings_filters(api):
    """[F-BKG-20] GET /bookings/me | B2 filters slot, status, date_from, date_to
    slot=DROP; status=CANCELLED; date range MON..TUE; date_from=TUE; slot+status combined.
    Expect: exactly the matching bookings in each case (range inclusive)"""
    e, b = _history(api)
    q = lambda **p: set(ids(api.get("/bookings/me", e.h, **p).json()))
    assert q(slot="DROP") == {b["mon_d"]["id"], b["tue_d"]["id"]}
    assert q(status="CANCELLED") == {b["tue_d"]["id"]}
    assert q(date_from=str(MON), date_to=str(TUE)) == {b["mon_p"]["id"], b["mon_d"]["id"], b["tue_d"]["id"]}
    assert q(date_from=str(TUE)) == {b["tue_d"]["id"], b["wed_p"]["id"]}
    assert q(date_to=str(MON)) == {b["mon_p"]["id"], b["mon_d"]["id"]}
    assert q(slot="DROP", status="BOOKED") == {b["mon_d"]["id"]}


@pytest.mark.parametrize("params", [{"date_from": "2026-09-30", "date_to": "2026-09-28"},
                                    {"sort_by": "zone"}, {"sort_by": "employee_id"}, {"status": "LOST"},
                                    {"slot": "NIGHT"}])
def test_my_bookings_invalid_params(api, params):
    """[F-BKG-21] GET /bookings/me | 5.3, 5.4
    date_from > date_to, non-whitelisted sort, bad enum values.
    Expect: 422"""
    assert api.get("/bookings/me", api.employee().h, **params).status_code == 422


def test_my_bookings_trip_summary(api):
    """[F-BKG-22] GET /bookings/me | B2 trip summary
    One booking assigned to a trip, one not.
    Expect: assigned item has trip {id, cab_registration_no, driver_name, driver_phone}; other has trip null"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=1)
    e = emps[0]
    api.book(e, TUE)
    items = {x["id"]: x for x in api.get("/bookings/me", e.h).json()["items"]}
    assigned = items[bookings[0]["id"]]
    cab = api.get(f"/cabs/{trip['cab_id']}", api.admin.h).json()
    assert assigned["trip_id"] == trip["id"] and assigned["trip"]["id"] == trip["id"]
    assert assigned["trip"]["cab_registration_no"] == cab["registration_no"]
    assert assigned["trip"]["driver_name"] == drv.data["full_name"]
    assert assigned["trip"]["driver_phone"] == drv.data["phone"]
    assert [x for x in items.values() if x["id"] != assigned["id"]][0]["trip"] is None


# ================================================================== B3 detail
def test_detail_other_employee_is_404(api):
    """[F-BKG-23] GET /bookings/{id} | B3, BR-12 style ownership
    Employee B opens employee A's booking.
    Expect: 404 (not 403)"""
    b = api.book(api.employee())
    assert api.get(f"/bookings/{b['id']}", api.employee().h).status_code == 404


def test_detail_admin_any_and_unknown(api):
    """[F-BKG-24] GET /bookings/{id} | B3
    Admin opens any booking; anyone opens unknown id.
    Expect: 200; unknown -> 404"""
    e = api.employee()
    b = api.book(e)
    assert api.get(f"/bookings/{b['id']}", api.admin.h).status_code == 200
    assert api.get("/bookings/98765", api.admin.h).status_code == 404
    assert api.get("/bookings/98765", e.h).status_code == 404


# ================================================================== B4 cancel
@pytest.mark.parametrize("slot,now,code", [
    ("PICKUP", ist(2026, 9, 28, 5, 29, 59), 200),
    ("PICKUP", ist(2026, 9, 28, 5, 30, 0), 422),
    ("PICKUP", ist(2026, 9, 28, 7, 0), 422),
    ("DROP", ist(2026, 9, 28, 15, 29, 59), 200),
    ("DROP", ist(2026, 9, 28, 15, 30, 0), 422),
])
def test_employee_cancel_cutoff(api, slot, now, code):
    """[F-BKG-25] PATCH /bookings/{id}/cancel | BR-06 cancel until 1 h before departure
    Cancel Mon PICKUP at 05:29:59 / 05:30:00 / 07:00 and Mon DROP at 15:29:59 / 15:30:00.
    Expect: 200 / 422 / 422 / 200 / 422"""
    e = api.employee()
    b = api.book(e, MON, slot)
    api.clock.set(now)
    r = api.patch(f"/bookings/{b['id']}/cancel", None, e.h)
    assert r.status_code == code
    expected = "CANCELLED" if code == 200 else "BOOKED"
    assert api.booking(b["id"])["status"] == expected


def test_cancel_sets_cancelled_at(api):
    """[F-BKG-26] PATCH /bookings/{id}/cancel | 4.4
    Cancel a booking.
    Expect: status CANCELLED and cancelled_at not null"""
    e = api.employee()
    b = api.book(e)
    r = api.patch(f"/bookings/{b['id']}/cancel", None, e.h).json()
    assert r["status"] == "CANCELLED" and r["cancelled_at"] is not None


def test_cancel_twice(api):
    """[F-BKG-27] PATCH /bookings/{id}/cancel | B4
    Cancel the same booking twice.
    Expect: second call 409"""
    e = api.employee()
    b = api.book(e)
    api.patch(f"/bookings/{b['id']}/cancel", None, e.h)
    assert api.patch(f"/bookings/{b['id']}/cancel", None, e.h).status_code == 409


def test_cancel_other_employees_booking(api):
    """[F-BKG-28] PATCH /bookings/{id}/cancel | B4 ownership
    Employee B cancels employee A's booking; unknown id.
    Expect: 404 and A's booking unchanged"""
    b = api.book(api.employee())
    assert api.patch(f"/bookings/{b['id']}/cancel", None, api.employee().h).status_code == 404
    assert api.booking(b["id"])["status"] == "BOOKED"
    assert api.patch("/bookings/55555/cancel", None, api.admin.h).status_code == 404


def test_cancel_assigned_frees_seat(api):
    """[F-BKG-29] PATCH /bookings/{id}/cancel | BR-06 seat freed
    2 passengers on a 4-seat trip; one cancels.
    Expect: booking CANCELLED with trip_id null; trip seats_booked 1, seats_available 3; passenger list has 1"""
    trip, _, emps, bookings = api.scheduled_trip(passengers=2, capacity=4)
    r = api.patch(f"/bookings/{bookings[0]['id']}/cancel", None, emps[0].h)
    assert r.status_code == 200 and r.json()["trip_id"] is None
    t = api.trip_detail(trip["id"])
    assert t["seats_booked"] == 1 and t["seats_available"] == 3 and len(t["passengers"]) == 1


def test_freed_seat_can_be_reused(api):
    """[F-BKG-30] PATCH /bookings/{id}/cancel + POST /trips/{id}/bookings | BR-06, BR-09
    Full 2-seat trip; one passenger cancels; admin assigns a new booking.
    Expect: assignment 200 (seat really freed)"""
    trip, _, emps, bookings = api.scheduled_trip(passengers=2, capacity=2)
    api.patch(f"/bookings/{bookings[0]['id']}/cancel", None, emps[0].h)
    nb = api.book(api.employee())
    assert api.assign(trip["id"], [nb["id"]]).status_code == 200


def test_admin_can_cancel_after_employee_cutoff(api):
    """[F-BKG-31] PATCH /bookings/{id}/cancel | B4 (admin not bound by cut-off)
    At Mon 05:45 (after employee cut-off, trip still SCHEDULED) admin cancels an assigned booking.
    Expect: 200 CANCELLED"""
    trip, _, _, bookings = api.scheduled_trip(passengers=1)
    api.clock.set(ist(2026, 9, 28, 5, 45))
    r = api.patch(f"/bookings/{bookings[0]['id']}/cancel", None, api.admin.h)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


def test_cannot_cancel_once_trip_started(api):
    """[F-BKG-32] PATCH /bookings/{id}/cancel | B4 (admin: before trip starts)
    Trip IN_PROGRESS; admin cancels an ASSIGNED passenger.
    Expect: 409"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    assert api.patch(f"/bookings/{bookings[0]['id']}/cancel", None, api.admin.h).status_code == 409


@pytest.mark.parametrize("final", ["BOARDED", "NO_SHOW", "COMPLETED"])
def test_cannot_cancel_finished_booking(api, final):
    """[F-BKG-33] PATCH /bookings/{id}/cancel | state machine 2.4
    Booking in BOARDED / NO_SHOW / COMPLETED; admin tries to cancel.
    Expect: 409"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    bid = bookings[0]["id"]
    api.start_trip(trip["id"], drv)
    if final in ("BOARDED", "COMPLETED"):
        api.patch(f"/driver/trips/{trip['id']}/bookings/{bid}", {"status": "BOARDED"}, drv.h)
    else:
        api.patch(f"/driver/trips/{trip['id']}/bookings/{bid}", {"status": "NO_SHOW"}, drv.h)
    if final == "COMPLETED":
        api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert api.booking(bid)["status"] == final
    assert api.patch(f"/bookings/{bid}/cancel", None, api.admin.h).status_code == 409


# ================================================================== B5 admin list
def _admin_population(api):
    east1 = api.employee(full_name="Kavya Rao", zone="EAST", employee_code="KR100")
    east2 = api.employee(full_name="Imran Ali", zone="EAST")
    west = api.employee(full_name="Pooja West", zone="WEST")
    a = api.book(east1, MON, "PICKUP")
    b = api.book(east2, MON, "PICKUP")
    c = api.book(west, MON, "PICKUP")
    d = api.book(east1, TUE, "DROP")
    e = api.book(east2, MON, "DROP")
    api.patch(f"/bookings/{e['id']}/cancel", None, east2.h)
    trip = api.trip()
    api.assign(trip["id"], [b["id"]])
    return dict(east1=east1, a=a, b=b, c=c, d=d, e=e)


def test_admin_list_filters(api):
    """[F-BKG-34] GET /bookings | B5 filters
    travel_date, slot, zone, status, employee_id, unassigned=true, q (name / employee_code).
    Expect: exact matching sets; unassigned excludes ASSIGNED and CANCELLED"""
    p = _admin_population(api)
    q = lambda **kw: set(ids(api.get("/bookings", api.admin.h, size=100, **kw).json()))
    assert q(travel_date=str(MON)) == {p["a"]["id"], p["b"]["id"], p["c"]["id"], p["e"]["id"]}
    assert q(slot="DROP") == {p["d"]["id"], p["e"]["id"]}
    assert q(zone="WEST") == {p["c"]["id"]}
    assert q(status="ASSIGNED") == {p["b"]["id"]}
    assert q(status="CANCELLED") == {p["e"]["id"]}
    assert q(employee_id=p["east1"].id) == {p["a"]["id"], p["d"]["id"]}
    assert q(unassigned="true") == {p["a"]["id"], p["c"]["id"], p["d"]["id"]}
    assert q(q="kavya") == {p["a"]["id"], p["d"]["id"]}
    assert q(q="kr1") == {p["a"]["id"], p["d"]["id"]}


def test_admin_list_combined_filters_and_total(api):
    """[F-BKG-35] GET /bookings | B5, 5.4 (AND) — the demo-script query
    travel_date=MON & slot=PICKUP & zone=EAST & unassigned=true.
    Expect: only Kavya's MON PICKUP; total 1"""
    p = _admin_population(api)
    r = api.get("/bookings", api.admin.h, travel_date=str(MON), slot="PICKUP", zone="EAST", unassigned="true").json()
    assert ids(r) == [p["a"]["id"]] and r["total"] == 1


def test_admin_list_sorting(api):
    """[F-BKG-36] GET /bookings | B5 sort
    Default (created_at asc), travel_date desc, zone asc.
    Expect: creation order; TUE first; EAST bookings before WEST"""
    p = _admin_population(api)
    order = [p[k]["id"] for k in ("a", "b", "c", "d", "e")]
    assert ids(api.get("/bookings", api.admin.h).json()) == order
    assert ids(api.get("/bookings", api.admin.h, sort_by="travel_date", order="desc").json())[0] == p["d"]["id"]
    zones = [x["zone"] for x in api.get("/bookings", api.admin.h, sort_by="zone").json()["items"]]
    assert zones == sorted(zones)


@pytest.mark.parametrize("params", [{"sort_by": "status"}, {"zone": "NOWHERE"}, {"unassigned": "sometimes"},
                                    {"travel_date": "tomorrow"}, {"employee_id": "abc"}])
def test_admin_list_invalid_params(api, params):
    """[F-BKG-37] GET /bookings | 5.3, 5.4
    Non-whitelisted sort, bad enum, bad bool, bad date, bad int.
    Expect: 422"""
    assert api.get("/bookings", api.admin.h, **params).status_code == 422
