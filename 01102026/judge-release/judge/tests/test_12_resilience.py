"""A10 Mishandling of Exceptional Conditions: hostile input never causes 5xx or leaks internals."""
import pytest

from checks import assert_envelope, assert_no_leak, assert_not_5xx
from harness import USERS

cat = pytest.mark.cat

HOSTILE_BODIES = {
    "deep_array": b"[" * 5000 + b"]" * 5000,
    "deep_object": b'{"a":' * 3000 + b"1" + b"}" * 3000,
    "huge_number": b'{"username": 1e999999, "password": "x"}',
    "big_int": b'{"username": 123456789012345678901234567890, "password": "x"}',
    "invalid_utf8": b'{"username": "\xff\xfe\xfd", "password": "x"}',
    "null_bytes": b'{"username": "asha\\u0000", "password": "x\\u0000"}',
    "lone_surrogate": b'{"username": "\\ud800", "password": "x"}',
    "duplicate_keys": b'{"username": "asha", "username": "farah", "password": "x"}',
    "bom_prefix": b'\xef\xbb\xbf{"username": "asha", "password": "x"}',
    "only_whitespace": b"   \n\t ",
    "true_literal": b"true",
    "long_string_value": b'{"username": "' + b"a" * 15000 + b'", "password": "x"}',
}


@cat("RESILIENCE")
@pytest.mark.parametrize("case", list(HOSTILE_BODIES))
def test_res_01_hostile_login_bodies(api, case):
    """RES-01 Hostile JSON on /auth/token -> 4xx envelope, no 5xx, no stack trace"""
    r = api.http.post("/api/v1/auth/token", content=HOSTILE_BODIES[case],
                      headers={"Content-Type": "application/json"})
    assert_not_5xx(r)
    assert_no_leak(r)
    assert_envelope(r, r.status_code)
    assert "access_token" not in r.text


@cat("RESILIENCE")
@pytest.mark.parametrize("case", list(HOSTILE_BODIES))
def test_res_02_hostile_decision_bodies(api, case):
    """RES-02 Hostile JSON on /decision -> 4xx envelope, no 5xx, no stack trace"""
    r = api.decide("priya", 1002, raw=HOSTILE_BODIES[case], headers={"Content-Type": "application/json"})
    assert_not_5xx(r)
    assert_no_leak(r)
    assert_envelope(r, r.status_code)


@cat("RESILIENCE")
@pytest.mark.parametrize("qs", ["q=%ff%fe", "q=" + "a" * 5000, "q=%F0%9F%A7%BE", "sort=%00", "page=1" + "0" * 400,
                                "status=" + ",".join(["SUBMITTED"] * 500), "employee_id=%E0%A5%A7",
                                "from_date=%EF%BC%92%EF%BC%90%EF%BC%92%EF%BC%96-07-01", "q[]=x", "q[$ne]=x"])
def test_res_03_hostile_query_strings(api, qs):
    """RES-03 Hostile query strings -> no 5xx, no stack trace"""
    r = api.http.get("/api/v1/expenses?" + qs, headers=api.auth("farah"))
    assert_not_5xx(r)
    assert_no_leak(r)


@cat("RESILIENCE")
def test_res_04_body_size_limit(api):
    """RES-04 Request body over 16 KB -> 413 payload_too_large"""
    big = {"username": "asha", "password": "x" * 20, "pad": "y" * 20000}
    assert_envelope(api.http.post("/api/v1/auth/token", json=big), 413, "payload_too_large")
    r = api.decide("priya", 1002, {"decision": "APPROVE", "comment": "z" * 20000})
    assert_envelope(r, 413, "payload_too_large")


@cat("RESILIENCE")
def test_res_05_request_id_generated(api):
    """RES-05 Every response carries a generated X-Request-ID when the client sends none"""
    ids = {api.http.get("/api/v1/expenses").headers.get("x-request-id") for _ in range(3)}
    assert None not in ids and "" not in ids and len(ids) == 3


@cat("RESILIENCE")
def test_res_06_request_id_echoed_when_valid(api):
    """RES-06 A well-formed client X-Request-ID (8-64 of A-Z a-z 0-9 -) is echoed back"""
    r = api.http.get("/api/v1/expenses", headers={"X-Request-ID": "judge-trace-000123"})
    assert r.headers.get("x-request-id") == "judge-trace-000123"
    assert r.json()["error"]["correlation_id"] == "judge-trace-000123"


@cat("RESILIENCE")
@pytest.mark.parametrize("rid", ["bad id with spaces", "<script>alert(1)</script>", "x" * 200, "short", "a;b=c"])
def test_res_07_request_id_not_reflected_when_invalid(api, rid):
    """RES-07 A malformed X-Request-ID is replaced, never reflected (header injection)"""
    r = api.http.get("/api/v1/expenses", headers={"X-Request-ID": rid})
    got = r.headers.get("x-request-id", "")
    assert got and got != rid


@cat("RESILIENCE")
def test_res_08_error_envelope_consistent(api):
    """RES-08 400/401/403/404/405/409/415 all use the same envelope with correlation_id"""
    h = api.auth("farah")
    cases = [
        (api.http.get("/api/v1/expenses?page=0", headers=h), 400),
        (api.http.get("/api/v1/expenses"), 401),
        (api.decide("asha", 1001), 403),
        (api.decide("priya", 9999), 404),
        (api.http.put("/api/v1/expenses", headers=h), 405),
        (api.decide("priya", 1003), 409),
        (api.http.post("/api/v1/auth/token", content=b"x", headers={"Content-Type": "text/plain"}), 415),
    ]
    for r, status in cases:
        assert_envelope(r, status)
        assert_no_leak(r)


@cat("RESILIENCE")
def test_res_09_service_healthy_after_abuse(api):
    """RES-09 After all the abuse above the service still works normally"""
    r = api.login_raw("neha", USERS["neha"]["password"])
    assert r.status_code == 200
    r2 = api.http.get("/api/v1/expenses", headers={"Authorization": "Bearer " + r.json()["access_token"]})
    assert r2.status_code == 200 and r2.json()["total"] == 5
