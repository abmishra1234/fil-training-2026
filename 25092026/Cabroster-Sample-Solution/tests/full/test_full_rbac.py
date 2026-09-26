"""FULL SUITE — authentication & role matrix across EVERY endpoint (section 3)."""
import pytest

from support import MON

pytestmark = pytest.mark.full

BOOK = {"travel_date": str(MON), "slot": "PICKUP"}
CAB = {"registration_no": "KA09ZZ9999", "model": "X", "capacity": 4}
STAFF = {"full_name": "Nobody", "email": "nobody@acmecorp.in", "phone": "9999999999", "password": "Passw0rd99",
         "role": "DRIVER", "license_no": "DL-NOBODY"}
TRIP = {"travel_date": str(MON), "slot": "PICKUP", "zone": "EAST", "cab_id": 999, "driver_id": 999}

# (method, path, json body, roles allowed)
ENDPOINTS = [
    ("GET", "/auth/me", None, {"ADMIN", "EMPLOYEE", "DRIVER"}),
    ("PATCH", "/auth/me", {"phone": "9123456780"}, {"ADMIN", "EMPLOYEE", "DRIVER"}),
    ("POST", "/users", STAFF, {"ADMIN"}),
    ("GET", "/users", None, {"ADMIN"}),
    ("GET", "/users/999", None, {"ADMIN"}),
    ("PATCH", "/users/999/status", {"is_active": False}, {"ADMIN"}),
    ("POST", "/cabs", CAB, {"ADMIN"}),
    ("GET", "/cabs", None, {"ADMIN"}),
    ("GET", "/cabs/999", None, {"ADMIN"}),
    ("PATCH", "/cabs/999", {"model": "Y"}, {"ADMIN"}),
    ("POST", "/bookings", BOOK, {"EMPLOYEE"}),
    ("GET", "/bookings/me", None, {"EMPLOYEE"}),
    ("GET", "/bookings", None, {"ADMIN"}),
    ("GET", "/bookings/999", None, {"ADMIN", "EMPLOYEE"}),
    ("PATCH", "/bookings/999/cancel", None, {"ADMIN", "EMPLOYEE"}),
    ("POST", "/trips", TRIP, {"ADMIN"}),
    ("GET", "/trips", None, {"ADMIN"}),
    ("GET", "/trips/999", None, {"ADMIN"}),
    ("POST", "/trips/999/bookings", {"booking_ids": [1]}, {"ADMIN"}),
    ("DELETE", "/trips/999/bookings/1", None, {"ADMIN"}),
    ("PATCH", "/trips/999/cancel", None, {"ADMIN"}),
    ("GET", "/driver/trips", None, {"DRIVER"}),
    ("GET", "/driver/trips/999", None, {"DRIVER"}),
    ("PATCH", "/driver/trips/999/start", None, {"DRIVER"}),
    ("PATCH", "/driver/trips/999/bookings/1", {"status": "BOARDED"}, {"DRIVER"}),
    ("PATCH", "/driver/trips/999/complete", None, {"DRIVER"}),
]


def _call(api, method, path, body, h):
    if method == "GET":
        return api.get(path, h)
    if method == "DELETE":
        return api.delete(path, h)
    return getattr(api, method.lower())(path, body, h)


@pytest.mark.parametrize("method,path,body,allowed", ENDPOINTS, ids=[f"{m} {p}" for m, p, *_ in ENDPOINTS])
def test_requires_authentication(api, method, path, body, allowed):
    """[F-RBAC-01] every protected endpoint | DEV-03, 5.5
    Call each of the 26 protected endpoints with no token.
    Expect: 401 on every one"""
    r = _call(api, method, path, body, None)
    assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


FORBIDDEN = [(m, p, b, role) for m, p, b, allowed in ENDPOINTS for role in ("ADMIN", "EMPLOYEE", "DRIVER")
             if role not in allowed]


@pytest.mark.parametrize("method,path,body,role", FORBIDDEN, ids=[f"{r}:{m} {p}" for m, p, _, r in FORBIDDEN])
def test_role_forbidden(api, method, path, body, role):
    """[F-RBAC-02] every protected endpoint | Section 3 permission matrix
    Call each endpoint with every role that is NOT allowed (IDs need not exist — role check comes first).
    Expect: 403 for every disallowed role/endpoint pair"""
    actor = {"ADMIN": lambda: api.admin, "EMPLOYEE": api.employee, "DRIVER": api.driver}[role]()
    r = _call(api, method, path, body, actor.h)
    assert r.status_code == 403, f"{role} {method} {path} -> {r.status_code}"


def test_public_endpoints_need_no_token(api):
    """[F-RBAC-03] POST /auth/register, POST /auth/login, GET /health | Section 3
    Call the public endpoints with no token.
    Expect: none of them returns 401/403"""
    assert api.register().status_code == 201
    assert api.login_resp("nobody@acmecorp.in", "x").status_code == 401  # bad creds, not missing token
    assert api.c.get("/health").status_code == 200
