"""API 1 - POST /api/v1/auth/token"""
import time

import jwt
import pytest

from checks import assert_envelope, assert_no_leak, assert_not_5xx
from harness import ISSUER, USERS, decode_segment

ACTIVE = [u for u, d in USERS.items() if d["is_active"] and u not in ("kiran", "sunil")]
cat = pytest.mark.cat


def err_sig(r):
    e = r.json()["error"]
    return (r.status_code, e["code"], e["message"])


# ------------------------------------------------------------------ happy path
@cat("AUTHN")
@pytest.mark.parametrize("username", ACTIVE)
def test_authn_01_every_active_user_can_log_in(api, username):
    """AUTHN-01 Every active seed user receives a bearer token"""
    r = api.login_raw(username, USERS[username]["password"])
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert set(body) >= {"access_token", "token_type", "expires_in"}
    assert body["token_type"].lower() == "bearer"
    assert isinstance(body["expires_in"], int) and 0 < body["expires_in"] <= 900


@cat("AUTHN")
def test_authn_02_token_response_not_cacheable(api):
    """AUTHN-02 Token response is JSON with Cache-Control: no-store"""
    r = api.login_raw("asha", USERS["asha"]["password"])
    assert r.headers.get("content-type", "").startswith("application/json")
    assert "no-store" in r.headers.get("cache-control", "").lower()


@cat("AUTHN")
def test_authn_03_token_signed_hs256_with_configured_secret(api, app):
    """AUTHN-03 Token is an HS256 JWT signed with JWT_SECRET and iss=expense-api"""
    tok = api.login_raw("asha", USERS["asha"]["password"]).json()["access_token"]
    assert decode_segment(tok.split(".")[0])["alg"] == "HS256"
    claims = jwt.decode(tok, app.secret, algorithms=["HS256"], issuer=ISSUER,
                        options={"require": ["exp", "iat", "sub", "iss"]})
    assert claims["sub"] == "1"


@cat("AUTHN")
def test_authn_04_token_is_short_lived(api, app):
    """AUTHN-04 Token lifetime (exp - iat) is at most 15 minutes"""
    tok = api.login_raw("ravi", USERS["ravi"]["password"]).json()["access_token"]
    c = jwt.decode(tok, app.secret, algorithms=["HS256"], issuer=ISSUER)
    assert 0 < c["exp"] - c["iat"] <= 900
    assert c["exp"] > time.time()


@cat("AUTHN")
@pytest.mark.parametrize("username", ["asha", "farah", "priya"])
def test_authn_05_token_contains_no_pii(api, username):
    """AUTHN-05 Token payload holds only minimal claims (no email, name, password, hash)"""
    tok = api.login_raw(username, USERS[username]["password"]).json()["access_token"]
    payload = decode_segment(tok.split(".")[1])
    allowed = {"sub", "iss", "iat", "exp", "jti", "nbf", "aud", "role", "typ", "token_type", "scope"}
    assert set(payload) <= allowed, f"unexpected claims: {set(payload) - allowed}"
    text = str(payload).lower()
    u = USERS[username]
    for secret in (u["email"], u["full_name"], u["password"], "argon", "$2b$", "pbkdf"):
        assert secret.lower() not in text


# ------------------------------------------------------------------ failures
@cat("AUTHN")
def test_authn_06_wrong_password_401(api):
    """AUTHN-06 Wrong password -> 401 invalid_credentials"""
    r = api.login_raw("asha", "Not-The-Right-Password-1")
    assert_envelope(r, 401, "invalid_credentials")


@cat("AUTHN")
def test_authn_07_no_user_enumeration(api):
    """AUTHN-07 Unknown user, wrong password and inactive user get IDENTICAL responses"""
    wrong = api.login_raw("ravi", "Not-The-Right-Password-1")
    unknown = api.login_raw("no.such.user", "Not-The-Right-Password-1")
    inactive = api.login_raw("dinesh", USERS["dinesh"]["password"])
    assert err_sig(wrong) == err_sig(unknown) == err_sig(inactive)
    assert wrong.status_code == 401


@cat("AUTHN")
def test_authn_08_inactive_user_cannot_log_in(api):
    """AUTHN-08 Disabled account with the correct password -> 401"""
    assert_envelope(api.login_raw("dinesh", USERS["dinesh"]["password"]), 401, "invalid_credentials")


@cat("AUTHN")
def test_authn_09_lockout_after_5_failures(api):
    """AUTHN-09 5 consecutive failures lock the account: correct password then fails"""
    for _ in range(5):
        assert api.login_raw("kiran", "Wrong-Password-Attempt-9").status_code == 401
    r = api.login_raw("kiran", USERS["kiran"]["password"])
    assert_envelope(r, 401, "invalid_credentials")


@cat("AUTHN")
def test_authn_10_locked_response_does_not_disclose_lock(api):
    """AUTHN-10 A locked account returns the same generic 401 (no 'locked' disclosure)"""
    locked = api.login_raw("kiran", USERS["kiran"]["password"])
    wrong = api.login_raw("asha", "Not-The-Right-Password-1")
    assert err_sig(locked) == err_sig(wrong)
    assert "lock" not in locked.text.lower()


@cat("AUTHN")
def test_authn_11_lockout_is_per_account(api):
    """AUTHN-11 Locking one account does not affect other users"""
    assert api.login_raw("asha", USERS["asha"]["password"]).status_code == 200


@cat("AUTHN")
def test_authn_12_success_resets_failure_counter(api):
    """AUTHN-12 A successful login resets the consecutive-failure counter"""
    pw = USERS["sunil"]["password"]
    for _ in range(4):
        assert api.login_raw("sunil", "Wrong-Password-Attempt-9").status_code == 401
    assert api.login_raw("sunil", pw).status_code == 200
    for _ in range(4):
        assert api.login_raw("sunil", "Wrong-Password-Attempt-9").status_code == 401
    assert api.login_raw("sunil", pw).status_code == 200


# ------------------------------------------------------------------ input validation
BAD_BODIES = {
    "missing_username": {"password": "x" * 20},
    "missing_password": {"username": "asha"},
    "empty_username": {"username": "", "password": "x" * 20},
    "empty_password": {"username": "asha", "password": ""},
    "username_65_chars": {"username": "a" * 65, "password": "x" * 20},
    "password_129_chars": {"username": "asha", "password": "x" * 129},
    "username_number": {"username": 12345, "password": "x" * 20},
    "password_null": {"username": "asha", "password": None},
    "password_object": {"username": "asha", "password": {"$ne": ""}},
    "username_array": {"username": ["asha"], "password": "x" * 20},
    "extra_role_field": {"username": "asha", "password": USERS["asha"]["password"], "role": "FINANCE_ADMIN"},
    "empty_object": {},
}


@cat("INPUT")
@pytest.mark.parametrize("case", list(BAD_BODIES))
def test_input_01_login_body_validation(api, case):
    """INPUT-01 Invalid login bodies -> 400 validation_error (never 401/500)"""
    r = api.http.post("/api/v1/auth/token", json=BAD_BODIES[case])
    assert_envelope(r, 400, "validation_error")


@cat("INPUT")
@pytest.mark.parametrize("raw", [b'{"username": "asha", "password": ', b"not json", b"[]", b'"asha"', b"null"])
def test_input_02_login_malformed_json(api, raw):
    """INPUT-02 Malformed / non-object JSON -> 400 validation_error"""
    r = api.http.post("/api/v1/auth/token", content=raw, headers={"Content-Type": "application/json"})
    assert_envelope(r, 400, "validation_error")


@cat("INPUT")
@pytest.mark.parametrize("ctype", ["text/plain", "application/x-www-form-urlencoded", "application/xml"])
def test_input_03_login_wrong_content_type(api, ctype):
    """INPUT-03 Non-JSON Content-Type -> 415 unsupported_media_type"""
    r = api.http.post("/api/v1/auth/token", content=b'{"username":"asha","password":"x"}',
                      headers={"Content-Type": ctype})
    assert_envelope(r, 415, "unsupported_media_type")


@cat("INPUT")
@pytest.mark.parametrize("payload", ["' OR '1'='1' --", "asha' --", "admin'/*", '" OR ""="', "asha\" OR 1=1 #",
                                     "*)(uid=*))(|(uid=*", "{\"$gt\": \"\"}"])
def test_input_04_login_injection_attempts_rejected(api, payload):
    """INPUT-04 Injection strings in username/password never authenticate or crash"""
    for body in ({"username": payload, "password": payload}, {"username": "asha", "password": payload}):
        r = api.http.post("/api/v1/auth/token", json=body)
        assert_not_5xx(r)
        assert r.status_code in (400, 401), r.text[:200]
        assert "access_token" not in r.text
        assert_no_leak(r)


@cat("CONFIG")
@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE", "PATCH"])
def test_config_01_login_wrong_method(api, method):
    """CONFIG-01 Only POST is allowed on /auth/token (405)"""
    r = api.http.request(method, "/api/v1/auth/token")
    assert_envelope(r, 405, "method_not_allowed")
