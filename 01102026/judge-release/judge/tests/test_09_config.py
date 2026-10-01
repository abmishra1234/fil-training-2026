"""A02 Security Misconfiguration: headers, CORS, HTTP methods, unknown routes."""
import re

import pytest

from checks import assert_envelope
from harness import ALLOWED_ORIGIN, USERS

cat = pytest.mark.cat


def sample_responses(api):
    h = api.auth("farah")
    return {
        "login_200": api.login_raw("farah", USERS["farah"]["password"]),
        "login_401": api.login_raw("farah", "Wrong-Password-Here-1"),
        "list_200": api.http.get("/api/v1/expenses", headers=h),
        "list_401": api.http.get("/api/v1/expenses"),
        "list_400": api.http.get("/api/v1/expenses?page=0", headers=h),
        "decision_404": api.decide("priya", 9999),
        "decision_403": api.decide("asha", 1001),
        "unknown_route": api.http.get("/api/v1/does-not-exist", headers=h),
        "method_405": api.http.delete("/api/v1/expenses", headers=h),
    }


@pytest.fixture(scope="module")
def samples(api):
    return sample_responses(api)


SAMPLE_KEYS = ["login_200", "login_401", "list_200", "list_401", "list_400", "decision_404",
               "decision_403", "unknown_route", "method_405"]


@cat("CONFIG")
@pytest.mark.parametrize("key", SAMPLE_KEYS)
def test_config_10_security_headers_everywhere(samples, key):
    """CONFIG-10 Security headers on every response, success AND error"""
    h = samples[key].headers
    assert h.get("x-content-type-options", "").lower() == "nosniff"
    assert "no-store" in h.get("cache-control", "").lower()
    assert h.get("x-frame-options", "").upper() == "DENY"
    assert "default-src 'none'" in h.get("content-security-policy", "")
    assert h.get("referrer-policy", "").lower() == "no-referrer"


@cat("CONFIG")
@pytest.mark.parametrize("key", SAMPLE_KEYS)
def test_config_11_no_technology_fingerprint(samples, key):
    """CONFIG-11 No X-Powered-By and no version number in the Server header"""
    h = samples[key].headers
    assert "x-powered-by" not in h
    assert not re.search(r"\d", h.get("server", "")), f"Server header discloses a version: {h.get('server')}"


@cat("CONFIG")
def test_config_12_cors_allowed_origin(api):
    """CONFIG-12 Preflight from the configured origin is allowed (exact origin, never *)"""
    r = api.http.options("/api/v1/expenses", headers={
        "Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization"})
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


@cat("CONFIG")
@pytest.mark.parametrize("origin", ["https://evil.example", "null", "https://expenses.example.com.evil.io",
                                    "http://expenses.example.com"])
def test_config_13_cors_rejects_other_origins(api, origin):
    """CONFIG-13 Other origins (look-alikes, http://, null) get no CORS permission"""
    pre = api.http.options("/api/v1/expenses", headers={
        "Origin": origin, "Access-Control-Request-Method": "GET"})
    get = api.http.get("/api/v1/expenses", headers={**api.auth("farah"), "Origin": origin})
    for r in (pre, get):
        acao = r.headers.get("access-control-allow-origin")
        assert acao not in (origin, "*"), f"CORS allowed {origin!r}: {acao}"


@cat("CONFIG")
@pytest.mark.parametrize("method,path", [("PUT", "/api/v1/expenses"), ("DELETE", "/api/v1/expenses"),
                                         ("PATCH", "/api/v1/expenses"), ("POST", "/api/v1/expenses"),
                                         ("GET", "/api/v1/expenses/1001/decision"),
                                         ("PUT", "/api/v1/expenses/1001/decision"),
                                         ("DELETE", "/api/v1/expenses/1001/decision"),
                                         ("TRACE", "/api/v1/expenses")])
def test_config_14_unsupported_methods(api, method, path):
    """CONFIG-14 Unsupported HTTP methods -> 405 method_not_allowed"""
    r = api.http.request(method, path, headers=api.auth("farah"))
    assert_envelope(r, 405, "method_not_allowed")


@cat("CONFIG")
@pytest.mark.parametrize("path", ["/api/v1/admin", "/api/v1/users", "/api/v1/expenses/1001",
                                  "/api/v2/expenses", "/.env", "/actuator/env", "/debug", "/api/v1/../../etc/passwd"])
def test_config_15_unknown_routes(api, path):
    """CONFIG-15 Unknown routes -> 404 (or 401) with the standard error envelope, nothing exposed"""
    r = api.http.get(path, headers=api.auth("farah"))
    assert r.status_code in (401, 404), f"{path}: {r.status_code}"
    assert_envelope(r, r.status_code)
