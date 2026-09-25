"""FULL SUITE — End-to-end behavioural flows (section 11 demo script + cross-module consistency)."""
import pytest

from support import MON, SAT, ids, ist

pytestmark = pytest.mark.full


def test_acceptance_demo_script(api):
    """[F-E2E-01] Section 11 demo script | BR-01…BR-15
    Runs all 17 demo steps in order with the fake clock.
    Expect: every step returns exactly the status/result listed in section 11"""
    # 1 admin login
    assert api.login_resp(api.admin.email, "Admin12345").json()["role"] == "ADMIN"
    # 2 register without address/zone -> cannot book
    e1 = api.employee(home_address=..., zone=...)
    assert api.book_resp(e1, MON).status_code == 422
    # 3 complete profile and book
    api.patch("/auth/me", {"home_address": "1 Indiranagar", "zone": "EAST"}, e1.h)
    b1 = api.book(e1, MON)
    assert b1["status"] == "BOOKED"
    # 4 duplicate
    assert api.book_resp(e1, MON).status_code == 409
    # 5 weekend
    assert api.book_resp(e1, SAT).status_code == 422
    # 6 four more EAST employees
    others = [api.employee(zone="EAST") for _ in range(4)]
    ob = [api.book(o, MON) for o in others]
    # 7 employee -> /users
    assert api.get("/users", e1.h).status_code == 403
    # 8 admin query
    r = api.get("/bookings", api.admin.h, travel_date=str(MON), slot="PICKUP", zone="EAST", unassigned="true",
                sort_by="created_at").json()
    assert r["total"] == 5 and ids(r) == [b1["id"]] + [b["id"] for b in ob]
    # 9 trip
    cab = api.cab(4)
    d1, d2 = api.driver(), api.driver()
    trip = api.trip(cab["id"], d1.id)
    # 10 same cab again
    assert api.trip_resp(cab["id"], d2.id).status_code == 409
    # 11 5 bookings on 4 seats -> nothing assigned
    all5 = [b1["id"]] + [b["id"] for b in ob]
    assert api.assign(trip["id"], all5).status_code == 409
    assert api.trip_detail(trip["id"])["seats_booked"] == 0
    # 12 assign 4
    r = api.assign(trip["id"], all5[:4])
    assert r.status_code == 200 and r.json()["seats_available"] == 0
    # 13 other driver
    assert api.get(f"/driver/trips/{trip['id']}", d2.h).status_code == 404
    # 14 start at 06:05
    api.clock.set(ist(2026, 9, 28, 6, 5))
    assert api.patch(f"/driver/trips/{trip['id']}/start", None, d1.h).json()["status"] == "IN_PROGRESS"
    # 15 board 3, complete
    for bid in all5[:3]:
        assert api.patch(f"/driver/trips/{trip['id']}/bookings/{bid}", {"status": "BOARDED"}, d1.h).status_code == 200
    assert api.patch(f"/driver/trips/{trip['id']}/complete", None, d1.h).status_code == 200
    statuses = [api.booking(b)["status"] for b in all5]
    assert statuses == ["COMPLETED", "COMPLETED", "COMPLETED", "NO_SHOW", "BOOKED"]
    # 16 DROP cancel after 15:30
    api.clock.set(ist(2026, 9, 28, 10, 0))
    drop = api.book(e1, MON, "DROP")
    api.clock.set(ist(2026, 9, 28, 15, 45))
    assert api.patch(f"/bookings/{drop['id']}/cancel", None, e1.h).status_code == 422
    # 17 my bookings newest first, paginated
    r = api.get("/bookings/me", e1.h, sort_by="travel_date", order="desc", page=1, size=5).json()
    assert r["total"] == 2 and r["page"] == 1 and r["size"] == 5


def test_reassign_after_trip_cancel(api):
    """[F-E2E-02] cancel trip -> re-assign | BR-16, BR-07, BR-10
    Trip with 2 passengers cancelled; new trip created with the SAME cab and driver; passengers re-assigned.
    Expect: all steps succeed; passengers show the new trip id"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=2)
    api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h)
    new = api.trip(trip["cab_id"], drv.id)
    assert api.assign(new["id"], [b["id"] for b in bookings]).status_code == 200
    assert all(api.booking(b["id"])["trip_id"] == new["id"] for b in bookings)


def test_pickup_and_drop_same_day_same_employee(api):
    """[F-E2E-03] full day | slots independent
    Employee rides PICKUP trip and DROP trip on the same day with different cabs/drivers.
    Expect: both bookings end COMPLETED; driver lists and statuses independent"""
    e = api.employee()
    bp = api.book(e, MON, "PICKUP")
    bd = api.book(e, MON, "DROP")
    tp, dp = api.trip(slot="PICKUP"), None
    td = api.trip(slot="DROP")
    api.assign(tp["id"], [bp["id"]])
    api.assign(td["id"], [bd["id"]])
    dp = api.trip_detail(tp["id"])["driver"]["id"]
    dd = api.trip_detail(td["id"])["driver"]["id"]
    # log drivers in via their e-mails from /users
    email = {u["id"]: u["email"] for u in api.get("/users", api.admin.h, role="DRIVER").json()["items"]}
    hp, hd = api.login(email[dp]), api.login(email[dd])
    for trip, h, bid, at in [(tp, hp, bp["id"], ist(2026, 9, 28, 6, 10)), (td, hd, bd["id"], ist(2026, 9, 28, 16, 10))]:
        api.clock.set(at)
        assert api.patch(f"/driver/trips/{trip['id']}/start", None, h).status_code == 200
        assert api.patch(f"/driver/trips/{trip['id']}/bookings/{bid}", {"status": "BOARDED"}, h).status_code == 200
        assert api.patch(f"/driver/trips/{trip['id']}/complete", None, h).status_code == 200
    assert api.booking(bp["id"])["status"] == "COMPLETED" and api.booking(bd["id"])["status"] == "COMPLETED"


def test_no_hard_deletes(api):
    """[F-E2E-04] soft delete | BR-06, BR-17
    Cancel booking, cancel trip, deactivate user and cab.
    Expect: all still retrievable by id afterwards"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=1)
    api.patch(f"/bookings/{bookings[0]['id']}/cancel", None, emps[0].h)
    api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h)
    api.patch(f"/users/{emps[0].id}/status", {"is_active": False}, api.admin.h)
    api.patch(f"/cabs/{trip['cab_id']}", {"is_active": False}, api.admin.h)
    for path in (f"/bookings/{bookings[0]['id']}", f"/trips/{trip['id']}", f"/users/{emps[0].id}",
                 f"/cabs/{trip['cab_id']}"):
        assert api.get(path, api.admin.h).status_code == 200, path


def test_no_server_errors_on_garbage_ids(api):
    """[F-E2E-05] robustness | 5.5
    Non-integer path ids on detail endpoints.
    Expect: 422 (never 500)"""
    e = api.employee()
    d = api.driver()
    assert api.get("/users/abc", api.admin.h).status_code == 422
    assert api.get("/cabs/abc", api.admin.h).status_code == 422
    assert api.get("/trips/abc", api.admin.h).status_code == 422
    assert api.get("/bookings/abc", e.h).status_code == 422
    assert api.get("/driver/trips/abc", d.h).status_code == 422
