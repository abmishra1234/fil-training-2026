"""FULL SUITE — Authentication, tokens and profile (A1–A4, DEV-03, DEV-04, BR-17)."""
import time

import pytest

from app.config import settings
from app.database import SessionLocal
from app.models import User
from support import PASSWORD, bearer, jwt_payload, make_hs256_token

pytestmark = pytest.mark.full

USER_READ_KEYS = {"id", "full_name", "email", "phone", "role", "employee_code", "home_address",
                  "zone", "license_no", "is_active", "created_at"}


def _no_password_keys(obj):
    if isinstance(obj, dict):
        return all("password" not in k.lower() and _no_password_keys(v) for k, v in obj.items())
    if isinstance(obj, list):
        return all(_no_password_keys(x) for x in obj)
    return True


# ------------------------------------------------------------------ register
def test_register_response_shape(api):
    """[F-AUTH-01] POST /auth/register | A1, 4.1
    Register and inspect the response body.
    Expect: 201; body has every UserRead field; role EMPLOYEE; license_no null"""
    r = api.register(zone="NORTH")
    assert r.status_code == 201
    body = r.json()
    assert USER_READ_KEYS <= body.keys()
    assert body["role"] == "EMPLOYEE" and body["license_no"] is None and body["zone"] == "NORTH"
    assert _no_password_keys(body)


def test_register_email_lowercased(api):
    """[F-AUTH-02] POST /auth/register | 4.1
    Register with a mixed-case e-mail.
    Expect: 201 and e-mail stored/returned in lower-case"""
    r = api.register(email="John.DOE@AcmeCorp.IN")
    assert r.status_code == 201 and r.json()["email"] == "john.doe@acmecorp.in"


def test_register_duplicate_email_case_insensitive(api):
    """[F-AUTH-03] POST /auth/register | A1
    Register 'a@x' then 'A@X' (same address, different case).
    Expect: second call 409"""
    assert api.register(email="dupe@acmecorp.in").status_code == 201
    assert api.register(email="DUPE@AcmeCorp.in").status_code == 409


def test_register_duplicate_employee_code(api):
    """[F-AUTH-04] POST /auth/register | A1, 4.1
    Two different e-mails with the same employee_code.
    Expect: second call 409"""
    assert api.register(employee_code="E-777").status_code == 201
    assert api.register(employee_code="E-777").status_code == 409


INVALID_REGISTRATIONS = {
    "missing full_name": {"full_name": ...},
    "full_name 1 char": {"full_name": "A"},
    "full_name 101 chars": {"full_name": "A" * 101},
    "missing email": {"email": ...},
    "malformed email": {"email": "not-an-email"},
    "missing phone": {"phone": ...},
    "phone 9 digits": {"phone": "987654321"},
    "phone 11 digits": {"phone": "98765432101"},
    "phone starts with 5": {"phone": "5876543210"},
    "phone has letters": {"phone": "98765abcde"},
    "phone with +91": {"phone": "+919876543210"},
    "missing password": {"password": ...},
    "password 7 chars": {"password": "Abcdef1"},
    "password no digit": {"password": "Abcdefghij"},
    "password no letter": {"password": "1234567890"},
    "missing employee_code": {"employee_code": ...},
    "employee_code 21 chars": {"employee_code": "E" * 21},
    "invalid zone": {"zone": "MARS"},
    "lower-case zone": {"zone": "east"},
    "home_address 256 chars": {"home_address": "x" * 256},
}


@pytest.mark.parametrize("case", INVALID_REGISTRATIONS.keys())
def test_register_validation(api, case):
    """[F-AUTH-05] POST /auth/register | A1, 4.1, 5.5
    Each invalid or missing field (20 variants: name length, e-mail, phone regex ^[6-9]\\d{9}$, password rules, code length, zone enum, address length).
    Expect: 422 for every variant"""
    r = api.register(**INVALID_REGISTRATIONS[case])
    assert r.status_code == 422, f"{case}: got {r.status_code}"


def test_register_boundary_values_accepted(api):
    """[F-AUTH-06] POST /auth/register | 4.1
    Boundary-valid values: 2-char name, 100-char name, 8-char password, 20-char code, phone starting 6.
    Expect: 201 for each"""
    assert api.register(full_name="Al").status_code == 201
    assert api.register(full_name="B" * 100).status_code == 201
    assert api.register(password="Abcdefg1").status_code == 201
    assert api.register(employee_code="C" * 20).status_code == 201
    assert api.register(phone="6000000000").status_code == 201


def test_register_without_address_and_zone(api):
    """[F-AUTH-07] POST /auth/register | A1
    Register without optional home_address and zone.
    Expect: 201 with both null"""
    r = api.register(home_address=..., zone=...)
    assert r.status_code == 201 and r.json()["home_address"] is None and r.json()["zone"] is None


def test_register_cannot_escalate_role(api):
    """[F-AUTH-08] POST /auth/register | A1, security
    Send role=ADMIN in the registration body.
    Expect: user is never ADMIN (either 422, or 201 with role EMPLOYEE)"""
    r = api.register(role="ADMIN", is_active=False)
    assert r.status_code in (201, 422)
    if r.status_code == 201:
        assert r.json()["role"] == "EMPLOYEE" and r.json()["is_active"] is True
        h = api.login(r.json()["email"])
        assert api.get("/auth/me", h).json()["role"] == "EMPLOYEE"


def test_password_is_hashed_in_db(api):
    """[F-AUTH-09] POST /auth/register | NFR security
    Look at the stored hashed_password column after registering.
    Expect: not equal to the plain password and is a bcrypt hash ($2...)"""
    e = api.employee()
    with SessionLocal() as s:
        stored = s.get(User, e.id).hashed_password
    assert stored != PASSWORD and stored.startswith("$2")


# ------------------------------------------------------------------ login
def test_login_email_case_insensitive(api):
    """[F-AUTH-10] POST /auth/login | A2
    Log in using an upper-cased version of the e-mail.
    Expect: 200"""
    e = api.employee()
    assert api.login_resp(e.email.upper()).status_code == 200


def test_login_unknown_email(api):
    """[F-AUTH-11] POST /auth/login | A2
    Log in with an e-mail that is not registered.
    Expect: 401"""
    assert api.login_resp("ghost@acmecorp.in").status_code == 401


def test_login_requires_form_data(api):
    """[F-AUTH-12] POST /auth/login | A2 (OAuth2 password flow)
    Send credentials as JSON instead of form fields.
    Expect: 422 (form fields username/password are required)"""
    e = api.employee()
    r = api.post("/auth/login", {"username": e.email, "password": PASSWORD})
    assert r.status_code == 422


def test_token_claims(api):
    """[F-AUTH-13] POST /auth/login | A2
    Decode the JWT payload.
    Expect: sub == str(user id), role == EMPLOYEE, exp ≈ 60 min from real time (55–65)"""
    e = api.employee()
    token = api.login_resp(e.email).json()["access_token"]
    p = jwt_payload(token)
    assert str(p["sub"]) == str(e.id) and p["role"] == "EMPLOYEE"
    minutes = (p["exp"] - time.time()) / 60
    assert 55 <= minutes <= 65, f"exp is {minutes:.1f} min away"


def test_login_returns_role_for_each_role(api):
    """[F-AUTH-14] POST /auth/login | A2
    Log in as admin, driver and employee.
    Expect: role field ADMIN / DRIVER / EMPLOYEE respectively"""
    drv = api.driver()
    emp = api.employee()
    assert api.login_resp(api.admin.email, "Admin12345").json()["role"] == "ADMIN"
    assert api.login_resp(drv.email).json()["role"] == "DRIVER"
    assert api.login_resp(emp.email).json()["role"] == "EMPLOYEE"


# ------------------------------------------------------------------ token validation
def test_missing_token_has_www_authenticate(api):
    """[F-AUTH-15] GET /auth/me | 5.5, DEV-03
    Call without Authorization header.
    Expect: 401 and header WWW-Authenticate: Bearer"""
    r = api.get("/auth/me")
    assert r.status_code == 401 and r.headers.get("www-authenticate", "").lower().startswith("bearer")


@pytest.mark.parametrize("header", ["Bearer abc.def.ghi", "Bearer ", "Basic dXNlcjpwYXNz", "abc"])
def test_malformed_tokens(api, header):
    """[F-AUTH-16] GET /auth/me | DEV-03
    Malformed Authorization headers (garbage JWT, empty bearer, Basic auth, no scheme).
    Expect: 401 for each"""
    assert api.get("/auth/me", {"Authorization": header}).status_code == 401


def test_token_signed_with_wrong_secret(api):
    """[F-AUTH-17] GET /auth/me | DEV-03
    Token with valid claims but signed with a different secret.
    Expect: 401"""
    e = api.employee()
    tok = make_hs256_token({"sub": str(e.id), "role": "EMPLOYEE", "exp": int(time.time()) + 600}, "wrong-secret")
    assert api.get("/auth/me", bearer(tok)).status_code == 401


def test_expired_token(api):
    """[F-AUTH-18] GET /auth/me | DEV-03
    Correctly signed token whose exp is 2 minutes in the past.
    Expect: 401"""
    e = api.employee()
    tok = make_hs256_token({"sub": str(e.id), "role": "EMPLOYEE", "exp": int(time.time()) - 120},
                           settings.JWT_SECRET_KEY)
    assert api.get("/auth/me", bearer(tok)).status_code == 401


def test_self_signed_valid_token_accepted(api):
    """[F-AUTH-19] GET /auth/me | Test Contract
    Hand-built HS256 token with settings.JWT_SECRET_KEY (proves contract settings are really used).
    Expect: 200 and correct user"""
    e = api.employee()
    tok = make_hs256_token({"sub": str(e.id), "role": "EMPLOYEE", "exp": int(time.time()) + 600},
                           settings.JWT_SECRET_KEY)
    r = api.get("/auth/me", bearer(tok))
    assert r.status_code == 200 and r.json()["id"] == e.id


def test_token_for_nonexistent_user(api):
    """[F-AUTH-20] GET /auth/me | DEV-03
    Valid signature, sub = 999999 (no such user).
    Expect: 401"""
    tok = make_hs256_token({"sub": "999999", "role": "ADMIN", "exp": int(time.time()) + 600},
                           settings.JWT_SECRET_KEY)
    assert api.get("/auth/me", bearer(tok)).status_code == 401


def test_token_without_sub(api):
    """[F-AUTH-21] GET /auth/me | DEV-03
    Valid signature but no 'sub' claim.
    Expect: 401"""
    tok = make_hs256_token({"role": "ADMIN", "exp": int(time.time()) + 600}, settings.JWT_SECRET_KEY)
    assert api.get("/auth/me", bearer(tok)).status_code == 401


def test_role_claim_is_not_trusted_for_authorisation(api):
    """[F-AUTH-22] GET /users | security
    Employee forges a token with role=ADMIN (signed correctly) — role must come from the DB user.
    Expect: 403 on an admin endpoint"""
    e = api.employee()
    tok = make_hs256_token({"sub": str(e.id), "role": "ADMIN", "exp": int(time.time()) + 600},
                           settings.JWT_SECRET_KEY)
    assert api.get("/users", bearer(tok)).status_code == 403


def test_deactivated_user_existing_token_rejected(api):
    """[F-AUTH-23] GET /auth/me | BR-17
    Employee logs in, admin deactivates them, employee reuses the old token.
    Expect: 401"""
    e = api.employee()
    assert api.patch(f"/users/{e.id}/status", {"is_active": False}, api.admin.h).status_code == 200
    assert api.get("/auth/me", e.h).status_code == 401


def test_inactive_user_login_rejected(api):
    """[F-AUTH-24] POST /auth/login | BR-17
    Deactivated user logs in with the correct password.
    Expect: 401"""
    e = api.employee()
    api.patch(f"/users/{e.id}/status", {"is_active": False}, api.admin.h)
    assert api.login_resp(e.email).status_code == 401


def test_password_never_exposed(api):
    """[F-AUTH-25] several | NFR security
    Inspect register, /auth/me, POST /users, GET /users, GET /users/{id} responses.
    Expect: no key containing 'password' anywhere"""
    e = api.employee()
    bodies = [
        api.get("/auth/me", e.h).json(),
        api.create_staff("DRIVER").json(),
        api.get("/users", api.admin.h).json(),
        api.get(f"/users/{e.id}", api.admin.h).json(),
        api.register().json(),
    ]
    assert all(_no_password_keys(b) for b in bodies)


# ------------------------------------------------------------------ profile
def test_update_profile_persists(api):
    """[F-AUTH-26] PATCH /auth/me | A4
    Update phone, address and zone, then GET /auth/me.
    Expect: 200 and GET shows the new values"""
    e = api.employee()
    r = api.patch("/auth/me", {"phone": "7000000001", "home_address": "Koramangala", "zone": "SOUTH"}, e.h)
    assert r.status_code == 200
    me = api.get("/auth/me", e.h).json()
    assert (me["phone"], me["home_address"], me["zone"]) == ("7000000001", "Koramangala", "SOUTH")


def test_update_profile_partial(api):
    """[F-AUTH-27] PATCH /auth/me | A4
    Update only the phone.
    Expect: 200; address and zone unchanged"""
    e = api.employee(zone="WEST", home_address="Old Address")
    r = api.patch("/auth/me", {"phone": "7000000002"}, e.h)
    assert r.status_code == 200 and r.json()["zone"] == "WEST" and r.json()["home_address"] == "Old Address"


@pytest.mark.parametrize("body", [{"phone": "12345"}, {"zone": "MOON"}, {"home_address": "x" * 256}])
def test_update_profile_validation(api, body):
    """[F-AUTH-28] PATCH /auth/me | A4, 4.1
    Invalid phone, zone or over-long address.
    Expect: 422"""
    e = api.employee()
    assert api.patch("/auth/me", body, e.h).status_code == 422


def test_update_profile_cannot_change_protected_fields(api):
    """[F-AUTH-29] PATCH /auth/me | A4
    Try to change role, email and is_active via PATCH /auth/me.
    Expect: afterwards role still EMPLOYEE, e-mail unchanged, still active"""
    e = api.employee()
    api.patch("/auth/me", {"role": "ADMIN", "email": "hacker@acmecorp.in", "is_active": False}, e.h)
    me = api.get("/auth/me", e.h)
    assert me.status_code == 200
    assert me.json()["role"] == "EMPLOYEE" and me.json()["email"] == e.email and me.json()["is_active"] is True


def test_driver_can_update_phone_only(api):
    """[F-AUTH-30] PATCH /auth/me | A4 (DRIVER: phone only)
    Driver updates phone, then tries address, then zone.
    Expect: phone 200; address 422; zone 422"""
    d = api.driver()
    assert api.patch("/auth/me", {"phone": "7111111111"}, d.h).status_code == 200
    assert api.patch("/auth/me", {"home_address": "Somewhere"}, d.h).status_code == 422
    assert api.patch("/auth/me", {"zone": "EAST"}, d.h).status_code == 422
