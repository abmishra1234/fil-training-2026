"""FULL SUITE — User management (U1–U4, DEV-07)."""
import pytest

from support import ids

pytestmark = pytest.mark.full


# ------------------------------------------------------------------ U1 create
def test_create_admin_without_license(api):
    """[F-USR-01] POST /users | U1
    Admin creates another ADMIN with no license_no.
    Expect: 201, role ADMIN, and the new admin can log in and list users"""
    r = api.create_staff("ADMIN")
    assert r.status_code == 201 and r.json()["role"] == "ADMIN"
    h = api.login(r.json()["email"])
    assert api.get("/users", h).status_code == 200


def test_create_driver_can_login(api):
    """[F-USR-02] POST /users | U1
    Admin creates a DRIVER; the driver logs in.
    Expect: 201 with license_no stored; login role DRIVER"""
    r = api.create_staff("DRIVER", license_no="KA0520200001")
    assert r.status_code == 201 and r.json()["license_no"] == "KA0520200001"
    assert api.login_resp(r.json()["email"]).json()["role"] == "DRIVER"


@pytest.mark.parametrize("role", ["EMPLOYEE", "SUPERUSER", "driver"])
def test_create_user_invalid_role(api, role):
    """[F-USR-03] POST /users | U1
    Role EMPLOYEE (employees must self-register), unknown role, lower-case role.
    Expect: 422"""
    body = api.staff_payload("DRIVER", license_no="DLX1")
    body["role"] = role
    r = api.post("/users", body, api.admin.h)
    assert r.status_code == 422


def test_create_driver_requires_license(api):
    """[F-USR-04] POST /users | U1
    Create a DRIVER without license_no.
    Expect: 422"""
    body = api.staff_payload("DRIVER")
    body.pop("license_no")
    assert api.post("/users", body, api.admin.h).status_code == 422


def test_create_user_duplicate_email_vs_employee(api):
    """[F-USR-05] POST /users | U1
    Admin creates a driver using an e-mail an employee already registered (different case).
    Expect: 409"""
    e = api.employee()
    r = api.create_staff("DRIVER", email=e.email.upper())
    assert r.status_code == 409


def test_create_driver_duplicate_license(api):
    """[F-USR-06] POST /users | U1, 4.1 unique license_no
    Two drivers with the same license number.
    Expect: second call 409"""
    assert api.create_staff("DRIVER", license_no="LIC-1").status_code == 201
    assert api.create_staff("DRIVER", license_no="LIC-1").status_code == 409


@pytest.mark.parametrize("field,value", [("phone", "123"), ("email", "bad"), ("password", "short1"),
                                         ("full_name", "X")])
def test_create_user_validation(api, field, value):
    """[F-USR-07] POST /users | U1, 4.1
    Invalid phone, e-mail, password, name.
    Expect: 422"""
    assert api.post("/users", api.staff_payload("DRIVER", **{field: value}), api.admin.h).status_code == 422


# ------------------------------------------------------------------ U2 list
def _population(api):
    e_east = api.employee(full_name="Zara East", zone="EAST", employee_code="ZE001")
    e_west = api.employee(full_name="Aman West", zone="WEST", employee_code="AW002")
    d = api.driver(full_name="Mohan Driver")
    inactive = api.employee(full_name="Ina Active", zone="EAST")
    api.patch(f"/users/{inactive.id}/status", {"is_active": False}, api.admin.h)
    return e_east, e_west, d, inactive


def test_list_users_filter_role(api):
    """[F-USR-08] GET /users | U2 filter role
    role=DRIVER and role=EMPLOYEE.
    Expect: only users of that role; total matches"""
    e_east, e_west, d, inactive = _population(api)
    r = api.get("/users", api.admin.h, role="DRIVER").json()
    assert ids(r) == [d.id] and r["total"] == 1
    r = api.get("/users", api.admin.h, role="EMPLOYEE").json()
    assert set(ids(r)) == {e_east.id, e_west.id, inactive.id} and r["total"] == 3


def test_list_users_filter_zone(api):
    """[F-USR-09] GET /users | U2 filter zone
    zone=WEST.
    Expect: only the WEST employee"""
    _, e_west, _, _ = _population(api)
    assert ids(api.get("/users", api.admin.h, zone="WEST").json()) == [e_west.id]


def test_list_users_filter_is_active(api):
    """[F-USR-10] GET /users | U2 filter is_active
    is_active=false then is_active=true.
    Expect: false -> only the deactivated user; true -> everyone else (incl. admin)"""
    *_, inactive = _population(api)
    assert ids(api.get("/users", api.admin.h, is_active="false").json()) == [inactive.id]
    active = api.get("/users", api.admin.h, is_active="true").json()
    assert inactive.id not in ids(active) and active["total"] == 4


@pytest.mark.parametrize("q,expected", [("zara", "e_east"), ("ZARA", "e_east"), ("aw002", "e_west"),
                                        ("mohan", "d"), ("driver", "d")])
def test_list_users_search(api, q, expected):
    """[F-USR-11] GET /users | U2 q (full_name, email, employee_code; case-insensitive)
    Search by partial name, upper-case name, employee_code, e-mail fragment.
    Expect: exactly the matching user"""
    e_east, e_west, d, _ = _population(api)
    target = {"e_east": e_east, "e_west": e_west, "d": d}[expected]
    assert ids(api.get("/users", api.admin.h, q=q).json()) == [target.id]


def test_list_users_filters_combine_with_and(api):
    """[F-USR-12] GET /users | 5.4 filters AND
    role=EMPLOYEE & zone=EAST & is_active=true.
    Expect: only the active EAST employee"""
    e_east, *_ = _population(api)
    r = api.get("/users", api.admin.h, role="EMPLOYEE", zone="EAST", is_active="true").json()
    assert ids(r) == [e_east.id] and r["total"] == 1


def test_list_users_sort_full_name(api):
    """[F-USR-13] GET /users | U2 sort full_name
    sort_by=full_name asc and desc.
    Expect: alphabetical and reverse-alphabetical order"""
    _population(api)
    names = [u["full_name"] for u in api.get("/users", api.admin.h, sort_by="full_name").json()["items"]]
    assert names == sorted(names)
    names_desc = [u["full_name"] for u in
                  api.get("/users", api.admin.h, sort_by="full_name", order="desc").json()["items"]]
    assert names_desc == sorted(names, reverse=True)


def test_list_users_sort_email(api):
    """[F-USR-14] GET /users | U2 sort email
    sort_by=email desc.
    Expect: e-mails in descending order"""
    _population(api)
    emails = [u["email"] for u in api.get("/users", api.admin.h, sort_by="email", order="desc").json()["items"]]
    assert emails == sorted(emails, reverse=True)


def test_list_users_default_sort_is_creation_order(api):
    """[F-USR-15] GET /users | U2 default sort created_at asc (ties by id)
    List without sort params.
    Expect: users in creation order (admin first)"""
    e_east, e_west, d, inactive = _population(api)
    assert ids(api.get("/users", api.admin.h).json()) == [api.admin.id, e_east.id, e_west.id, d.id, inactive.id]


@pytest.mark.parametrize("params", [{"sort_by": "hashed_password"}, {"sort_by": "role"}, {"order": "up"},
                                    {"role": "KING"}, {"zone": "MARS"}, {"is_active": "maybe"}])
def test_list_users_invalid_params(api, params):
    """[F-USR-16] GET /users | 5.3 whitelist, 5.4 enums
    Non-whitelisted sort_by, bad order, bad enum filters.
    Expect: 422"""
    assert api.get("/users", api.admin.h, **params).status_code == 422


# ------------------------------------------------------------------ U3 / U4
def test_get_user_not_found(api):
    """[F-USR-17] GET /users/{id} | U3
    Unknown id.
    Expect: 404"""
    assert api.get("/users/424242", api.admin.h).status_code == 404


def test_status_not_found(api):
    """[F-USR-18] PATCH /users/{id}/status | U4
    Unknown id.
    Expect: 404"""
    assert api.patch("/users/424242/status", {"is_active": False}, api.admin.h).status_code == 404


def test_admin_cannot_deactivate_self(api):
    """[F-USR-19] PATCH /users/{id}/status | U4
    Admin tries to deactivate own account.
    Expect: 409 and admin still able to call admin APIs"""
    assert api.patch(f"/users/{api.admin.id}/status", {"is_active": False}, api.admin.h).status_code == 409
    assert api.get("/users", api.admin.h).status_code == 200


def test_reactivate_user(api):
    """[F-USR-20] PATCH /users/{id}/status | U4, BR-17
    Deactivate then reactivate an employee.
    Expect: login 401 while inactive, 200 after reactivation"""
    e = api.employee()
    api.patch(f"/users/{e.id}/status", {"is_active": False}, api.admin.h)
    assert api.login_resp(e.email).status_code == 401
    r = api.patch(f"/users/{e.id}/status", {"is_active": True}, api.admin.h)
    assert r.status_code == 200 and r.json()["is_active"] is True
    assert api.login_resp(e.email).status_code == 200


@pytest.mark.parametrize("body", [{}, {"is_active": "perhaps"}])
def test_status_validation(api, body):
    """[F-USR-21] PATCH /users/{id}/status | U4
    Missing or non-boolean is_active.
    Expect: 422"""
    e = api.employee()
    assert api.patch(f"/users/{e.id}/status", body, api.admin.h).status_code == 422


def test_deactivated_driver_cannot_be_assigned_to_trip(api):
    """[F-USR-22] POST /trips | BR-08, BR-17
    Deactivate a driver then create a trip with them.
    Expect: 422"""
    d = api.driver()
    api.patch(f"/users/{d.id}/status", {"is_active": False}, api.admin.h)
    assert api.trip_resp(api.cab()["id"], d.id).status_code == 422
