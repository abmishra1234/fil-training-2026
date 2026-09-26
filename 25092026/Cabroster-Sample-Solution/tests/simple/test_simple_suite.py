"""SIMPLE SUITE — one or two basic checks per API.

Goal: confirm every endpoint exists, is wired to the right role and returns the
agreed shape for the normal ("happy") path. Passing this suite means the skeleton
is complete; it does NOT mean the business rules are correct (see tests/full).

Docstring format (used to build the Excel catalogue):
    [ID] METHOD /path | rule refs
    What the test does.
    Expect: expected outcome
"""
import pytest

from support import MON, PASSWORD, TUE, ist

pytestmark = pytest.mark.simple


# ---------------------------------------------------------------- health
def test_health(client):
    """[S-HLT-01] GET /health | DEV-01
    Call the health endpoint without a token.
    Expect: 200 and body {"status": "ok"}"""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------- auth
def test_register_employee(api):
    """[S-AUTH-01] POST /auth/register | A1
    Register a new employee with valid data.
    Expect: 201, role EMPLOYEE, is_active true, no password fields in response"""
    r = api.register()
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "EMPLOYEE" and body["is_active"] is True
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email(api):
    """[S-AUTH-02] POST /auth/register | A1
    Register twice with the same e-mail.
    Expect: second call 409"""
    first = api.register(email="dup@acmecorp.in")
    assert first.status_code == 201
    assert api.register(email="dup@acmecorp.in").status_code == 409


def test_login_success(api):
    """[S-AUTH-03] POST /auth/login | A2
    Log in with correct credentials (OAuth2 form).
    Expect: 200 with access_token, token_type 'bearer' and role"""
    e = api.employee()
    r = api.login_resp(e.email)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["token_type"].lower() == "bearer" and body["role"] == "EMPLOYEE"


def test_login_wrong_password(api):
    """[S-AUTH-04] POST /auth/login | A2
    Log in with a wrong password.
    Expect: 401"""
    e = api.employee()
    assert api.login_resp(e.email, "Wrong12345").status_code == 401


def test_me(api):
    """[S-AUTH-05] GET /auth/me | A3
    Fetch own profile with a valid token.
    Expect: 200 and the same id/email as registered"""
    e = api.employee()
    r = api.get("/auth/me", e.h)
    assert r.status_code == 200 and r.json()["id"] == e.id and r.json()["email"] == e.email


def test_me_without_token(api):
    """[S-AUTH-06] GET /auth/me | DEV-03
    Call a protected endpoint without a token.
    Expect: 401"""
    assert api.get("/auth/me").status_code == 401


def test_update_me(api):
    """[S-AUTH-07] PATCH /auth/me | A4
    Employee updates own address and zone.
    Expect: 200 and new values returned"""
    e = api.employee(zone="EAST")
    r = api.patch("/auth/me", {"home_address": "22 MG Road", "zone": "WEST"}, e.h)
    assert r.status_code == 200 and r.json()["zone"] == "WEST" and r.json()["home_address"] == "22 MG Road"


# ---------------------------------------------------------------- users
def test_admin_creates_driver(api):
    """[S-USR-01] POST /users | U1
    Admin creates a DRIVER with a license number.
    Expect: 201 and role DRIVER"""
    r = api.create_staff("DRIVER")
    assert r.status_code == 201 and r.json()["role"] == "DRIVER"


def test_employee_cannot_create_user(api):
    """[S-USR-02] POST /users | U1, RBAC
    Employee tries to create a driver.
    Expect: 403"""
    e = api.employee()
    assert api.post("/users", api.staff_payload("DRIVER"), e.h).status_code == 403


def test_list_users_paginated(api):
    """[S-USR-03] GET /users | U2
    Admin lists users.
    Expect: 200 and a pagination envelope (items, total, page, size, pages)"""
    api.employee()
    r = api.get("/users", api.admin.h)
    assert r.status_code == 200
    assert {"items", "total", "page", "size", "pages"} <= r.json().keys()
    assert r.json()["total"] == 2  # admin + employee


def test_get_user(api):
    """[S-USR-04] GET /users/{id} | U3
    Admin fetches one user by id.
    Expect: 200 and the right user"""
    e = api.employee()
    r = api.get(f"/users/{e.id}", api.admin.h)
    assert r.status_code == 200 and r.json()["email"] == e.email


def test_deactivate_user(api):
    """[S-USR-05] PATCH /users/{id}/status | U4, BR-17
    Admin deactivates an employee, who then tries to log in.
    Expect: 200 with is_active false; login afterwards 401"""
    e = api.employee()
    r = api.patch(f"/users/{e.id}/status", {"is_active": False}, api.admin.h)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert api.login_resp(e.email).status_code == 401


# ---------------------------------------------------------------- cabs
def test_create_cab(api):
    """[S-CAB-01] POST /cabs | C1
    Admin creates a cab with a lower-case registration number.
    Expect: 201, registration stored upper-case, is_active true"""
    r = api.post("/cabs", {"registration_no": "ka01ab1234", "model": "Dzire", "capacity": 4}, api.admin.h)
    assert r.status_code == 201
    assert r.json()["registration_no"] == "KA01AB1234" and r.json()["is_active"] is True


def test_create_cab_duplicate(api):
    """[S-CAB-02] POST /cabs | C1
    Create two cabs with the same registration number.
    Expect: second call 409"""
    api.cab(registration_no="KA05MN4321")
    r = api.post("/cabs", api.cab_payload(registration_no="KA05MN4321"), api.admin.h)
    assert r.status_code == 409


def test_list_cabs(api):
    """[S-CAB-03] GET /cabs | C2
    Admin lists cabs sorted by capacity descending.
    Expect: 200, biggest cab first"""
    api.cab(4)
    big = api.cab(6)
    r = api.get("/cabs", api.admin.h, sort_by="capacity", order="desc")
    assert r.status_code == 200 and r.json()["items"][0]["id"] == big["id"]


def test_get_cab(api):
    """[S-CAB-04] GET /cabs/{id} | C3
    Admin fetches a cab by id.
    Expect: 200 and same registration number"""
    cab = api.cab()
    r = api.get(f"/cabs/{cab['id']}", api.admin.h)
    assert r.status_code == 200 and r.json()["registration_no"] == cab["registration_no"]


def test_update_cab(api):
    """[S-CAB-05] PATCH /cabs/{id} | C4
    Admin changes model and capacity.
    Expect: 200 and updated values"""
    cab = api.cab(4)
    r = api.patch(f"/cabs/{cab['id']}", {"model": "Innova", "capacity": 6}, api.admin.h)
    assert r.status_code == 200 and r.json()["capacity"] == 6 and r.json()["model"] == "Innova"


# ---------------------------------------------------------------- bookings
def test_create_booking(api):
    """[S-BKG-01] POST /bookings | B1
    Employee books PICKUP for next Monday (now = Fri 10:00).
    Expect: 201, status BOOKED, zone/address copied from profile, trip null"""
    e = api.employee(zone="EAST", home_address="12 Indiranagar")
    r = api.book_resp(e, MON, "PICKUP")
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "BOOKED" and b["zone"] == "EAST"
    assert b["pickup_drop_address"] == "12 Indiranagar" and b["trip"] is None and b["employee_id"] == e.id


def test_create_booking_duplicate(api):
    """[S-BKG-02] POST /bookings | BR-03
    Book the same date and slot twice.
    Expect: second call 409"""
    e = api.employee()
    api.book(e, MON, "PICKUP")
    assert api.book_resp(e, MON, "PICKUP").status_code == 409


def test_my_bookings(api):
    """[S-BKG-03] GET /bookings/me | B2
    Employee with two bookings lists own bookings.
    Expect: 200, total 2, newest travel date first (default sort)"""
    e = api.employee()
    api.book(e, MON)
    later = api.book(e, TUE)
    r = api.get("/bookings/me", e.h)
    assert r.status_code == 200 and r.json()["total"] == 2
    assert r.json()["items"][0]["id"] == later["id"]


def test_get_booking(api):
    """[S-BKG-04] GET /bookings/{id} | B3
    Employee opens own booking.
    Expect: 200 and same booking id"""
    e = api.employee()
    b = api.book(e)
    r = api.get(f"/bookings/{b['id']}", e.h)
    assert r.status_code == 200 and r.json()["id"] == b["id"]


def test_cancel_booking(api):
    """[S-BKG-05] PATCH /bookings/{id}/cancel | B4, BR-06
    Employee cancels own booking well before the cut-off.
    Expect: 200 and status CANCELLED"""
    e = api.employee()
    b = api.book(e)
    r = api.patch(f"/bookings/{b['id']}/cancel", None, e.h)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


def test_admin_list_bookings(api):
    """[S-BKG-06] GET /bookings | B5
    Admin filters bookings by date and slot.
    Expect: 200 and only the matching booking"""
    e = api.employee()
    pickup = api.book(e, MON, "PICKUP")
    api.book(e, MON, "DROP")
    r = api.get("/bookings", api.admin.h, travel_date=str(MON), slot="PICKUP")
    assert r.status_code == 200 and [x["id"] for x in r.json()["items"]] == [pickup["id"]]


# ---------------------------------------------------------------- trips
def test_create_trip(api):
    """[S-TRP-01] POST /trips | T1
    Admin creates a trip with an active cab and driver.
    Expect: 201, status SCHEDULED, seats_available = capacity"""
    cab = api.cab(4)
    drv = api.driver()
    r = api.trip_resp(cab["id"], drv.id)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "SCHEDULED" and r.json()["seats_available"] == 4 and r.json()["seats_booked"] == 0


def test_list_trips(api):
    """[S-TRP-02] GET /trips | T2
    Admin lists trips for a date.
    Expect: 200, total 1"""
    api.trip()
    r = api.get("/trips", api.admin.h, travel_date=str(MON))
    assert r.status_code == 200 and r.json()["total"] == 1


def test_get_trip_detail(api):
    """[S-TRP-03] GET /trips/{id} | T3
    Admin opens a trip that has one passenger.
    Expect: 200 with cab, driver and 1 passenger"""
    trip, drv, emps, bookings = api.scheduled_trip(passengers=1)
    r = api.get(f"/trips/{trip['id']}", api.admin.h)
    assert r.status_code == 200
    body = r.json()
    assert body["cab"]["id"] == trip["cab_id"] and body["driver"]["id"] == drv.id
    assert len(body["passengers"]) == 1


def test_assign_bookings(api):
    """[S-TRP-04] POST /trips/{id}/bookings | T4, BR-10
    Admin assigns two matching bookings to a trip.
    Expect: 200, seats_booked 2 and bookings now ASSIGNED"""
    trip = api.trip(capacity=4)
    b1 = api.book(api.employee())
    b2 = api.book(api.employee())
    r = api.assign(trip["id"], [b1["id"], b2["id"]])
    assert r.status_code == 200 and r.json()["seats_booked"] == 2
    assert api.booking(b1["id"])["status"] == "ASSIGNED"


def test_assign_over_capacity(api):
    """[S-TRP-05] POST /trips/{id}/bookings | BR-09
    Assign 3 bookings to a 2-seat cab.
    Expect: 409"""
    trip = api.trip(capacity=2)
    bs = [api.book(api.employee())["id"] for _ in range(3)]
    assert api.assign(trip["id"], bs).status_code == 409


def test_remove_booking_from_trip(api):
    """[S-TRP-06] DELETE /trips/{id}/bookings/{booking_id} | T5
    Admin removes an assigned booking from a scheduled trip.
    Expect: 200/204 and booking back to BOOKED with no trip"""
    trip, _, _, bookings = api.scheduled_trip(passengers=1)
    r = api.delete(f"/trips/{trip['id']}/bookings/{bookings[0]['id']}", api.admin.h)
    assert r.status_code in (200, 204)
    b = api.booking(bookings[0]["id"])
    assert b["status"] == "BOOKED" and b["trip_id"] is None


def test_cancel_trip(api):
    """[S-TRP-07] PATCH /trips/{id}/cancel | T6, BR-16
    Admin cancels a scheduled trip.
    Expect: 200, trip CANCELLED"""
    trip = api.trip()
    r = api.patch(f"/trips/{trip['id']}/cancel", None, api.admin.h)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


# ---------------------------------------------------------------- driver
def test_driver_lists_own_trips(api):
    """[S-DRV-01] GET /driver/trips | D1
    Driver lists own trips.
    Expect: 200, total 1"""
    trip, drv, _, _ = api.scheduled_trip(passengers=0)
    r = api.get("/driver/trips", drv.h)
    assert r.status_code == 200 and r.json()["total"] == 1 and r.json()["items"][0]["id"] == trip["id"]


def test_driver_manifest(api):
    """[S-DRV-02] GET /driver/trips/{id} | D2
    Driver opens the manifest of own trip.
    Expect: 200 with passenger name and phone"""
    trip, drv, emps, _ = api.scheduled_trip(passengers=1)
    r = api.get(f"/driver/trips/{trip['id']}", drv.h)
    assert r.status_code == 200
    p = r.json()["passengers"][0]
    assert p["employee_name"] == emps[0].data["full_name"] and p["employee_phone"] == emps[0].data["phone"]


def test_driver_start_trip(api):
    """[S-DRV-03] PATCH /driver/trips/{id}/start | D3
    Driver starts a PICKUP trip at 06:05 on the travel date.
    Expect: 200, status IN_PROGRESS"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1)
    api.clock.set(ist(2026, 9, 28, 6, 5))
    r = api.patch(f"/driver/trips/{trip['id']}/start", None, drv.h)
    assert r.status_code == 200 and r.json()["status"] == "IN_PROGRESS"


def test_driver_marks_boarded(api):
    """[S-DRV-04] PATCH /driver/trips/{id}/bookings/{booking_id} | D4
    Driver marks a passenger BOARDED on an in-progress trip.
    Expect: 200 and booking status BOARDED"""
    trip, drv, _, bookings = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    r = api.patch(f"/driver/trips/{trip['id']}/bookings/{bookings[0]['id']}", {"status": "BOARDED"}, drv.h)
    assert r.status_code == 200
    assert api.booking(bookings[0]["id"])["status"] == "BOARDED"


def test_driver_completes_trip(api):
    """[S-DRV-05] PATCH /driver/trips/{id}/complete | D5
    Driver completes an in-progress trip.
    Expect: 200, status COMPLETED"""
    trip, drv, _, _ = api.scheduled_trip(passengers=1)
    api.start_trip(trip["id"], drv)
    r = api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"


def test_driver_cannot_see_admin_lists(api):
    """[S-DRV-06] GET /trips | RBAC
    Driver calls the admin trips list.
    Expect: 403"""
    drv = api.driver()
    assert api.get("/trips", drv.h).status_code == 403


# ---------------------------------------------------------------- end-to-end smoke
def test_happy_path_end_to_end(api):
    """[S-E2E-01] Full flow | Demo script
    Employee books, admin creates trip and assigns, driver starts, marks boarded and completes; employee sees result.
    Expect: final booking status COMPLETED with trip summary showing cab and driver"""
    e = api.employee(zone="EAST")
    b = api.book(e, MON, "PICKUP")
    cab = api.cab(4)
    drv = api.driver()
    trip = api.trip(cab["id"], drv.id)
    assert api.assign(trip["id"], [b["id"]]).status_code == 200
    api.start_trip(trip["id"], drv)
    api.patch(f"/driver/trips/{trip['id']}/bookings/{b['id']}", {"status": "BOARDED"}, drv.h)
    api.patch(f"/driver/trips/{trip['id']}/complete", None, drv.h)
    mine = api.get(f"/bookings/{b['id']}", e.h).json()
    assert mine["status"] == "COMPLETED"
    assert mine["trip"]["cab_registration_no"] == cab["registration_no"]
    assert mine["trip"]["driver_name"] == drv.data["full_name"]
