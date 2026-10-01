"""A02/A04: the service must refuse unsafe configuration and hide dev tooling in production."""
import secrets

import httpx
import pytest

from harness import AppProcess, USERS

cat = pytest.mark.cat
GOOD_SECRET = secrets.token_urlsafe(48)


def refuses(overrides=None, drop=()):
    p = AppProcess(overrides, drop)
    try:
        started = p.start(expect_failure=True)
        if started:
            return False, p.log_text()
        return p.exited_with_error(), p.log_text()
    finally:
        p.stop()


@cat("CONFIG")
def test_prod_01_missing_secret():
    """PROD-01 APP_ENV=prod without JWT_SECRET -> process exits with a non-zero code"""
    ok, log = refuses({"APP_ENV": "prod"}, drop=("JWT_SECRET",))
    assert ok, "app must refuse to start without JWT_SECRET"


@cat("CONFIG")
@pytest.mark.parametrize("secret", ["secret", "changeme", "x" * 31])
def test_prod_02_weak_secret(secret):
    """PROD-02 JWT_SECRET shorter than 32 bytes -> refuse to start"""
    ok, _ = refuses({"APP_ENV": "prod", "JWT_SECRET": secret})
    assert ok


@cat("CONFIG")
def test_prod_03_wildcard_cors():
    """PROD-03 CORS_ALLOWED_ORIGINS=* -> refuse to start"""
    ok, _ = refuses({"APP_ENV": "prod", "JWT_SECRET": GOOD_SECRET, "CORS_ALLOWED_ORIGINS": "*"})
    assert ok


@cat("CONFIG")
def test_prod_04_invalid_app_env():
    """PROD-04 APP_ENV other than test|prod (e.g. dev) -> refuse to start"""
    ok, _ = refuses({"APP_ENV": "dev", "JWT_SECRET": GOOD_SECRET})
    assert ok


@cat("CONFIG")
def test_prod_05_secret_not_logged_on_failure():
    """PROD-05 A rejected secret is never echoed into the logs"""
    weak = "weak-secret-" + secrets.token_hex(4)
    _, log = refuses({"APP_ENV": "prod", "JWT_SECRET": weak})
    assert weak not in log


@pytest.fixture(scope="module")
def prod():
    p = AppProcess({"APP_ENV": "prod", "JWT_SECRET": "p" * 32})      # 32 bytes = minimum, must start
    started = p.start()
    yield p if started else None
    p.stop()


@cat("CONFIG")
def test_prod_06_boundary_secret_starts(prod):
    """PROD-06 A 32-byte secret is accepted and the prod service starts"""
    assert prod is not None, "app must start in prod with a 32-byte secret"


@cat("CONFIG")
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/swagger-ui/index.html", "/swagger-ui.html",
                                  "/v3/api-docs", "/swagger", "/swagger/index.html", "/actuator"])
def test_prod_07_no_api_explorer_in_prod(prod, path):
    """PROD-07 Interactive docs / OpenAPI / actuator are NOT served in prod"""
    assert prod is not None
    r = httpx.get(prod.base_url + path, timeout=10)
    assert r.status_code in (401, 403, 404), f"{path} returned {r.status_code} in prod"


@cat("CONFIG")
def test_prod_08_prod_still_works(prod):
    """PROD-08 Login + list work in prod mode"""
    assert prod is not None
    r = httpx.post(prod.base_url + "/api/v1/auth/token", timeout=10,
                   json={"username": "asha", "password": USERS["asha"]["password"]})
    assert r.status_code == 200
    r2 = httpx.get(prod.base_url + "/api/v1/expenses", timeout=10,
                   headers={"Authorization": "Bearer " + r.json()["access_token"]})
    assert r2.status_code == 200 and r2.json()["total"] == 8


@cat("CONFIG")
def test_prod_09_secure_default_env():
    """PROD-09 APP_ENV unset defaults to prod behaviour (docs hidden)"""
    p = AppProcess({"JWT_SECRET": GOOD_SECRET}, drop=("APP_ENV",))
    try:
        assert p.start(), "app must start with APP_ENV unset"
        for path in ("/docs", "/openapi.json", "/swagger-ui/index.html", "/v3/api-docs"):
            assert httpx.get(p.base_url + path, timeout=10).status_code in (401, 403, 404)
    finally:
        p.stop()
