"""API 1 - login throttling (configured LOGIN_RATE_LIMIT_PER_MINUTE=5 for this module)."""
import pytest

from checks import assert_envelope
from harness import USERS

APP_ENV_OVERRIDES = {"LOGIN_RATE_LIMIT_PER_MINUTE": "5"}
cat = pytest.mark.cat


@cat("AUTHN")
def test_authn_20_rate_limit_after_threshold(api):
    """AUTHN-20 More than LOGIN_RATE_LIMIT_PER_MINUTE attempts from one client -> 429"""
    for i in range(5):
        r = api.login_raw("ravi", f"Wrong-Password-{i}-xxxxx")
        assert r.status_code != 429, f"throttled too early at attempt {i + 1}"
    r = api.login_raw("ravi", "Wrong-Password-6-xxxxx")
    assert_envelope(r, 429, "rate_limited")


@cat("AUTHN")
def test_authn_21_retry_after_header(api):
    """AUTHN-21 429 response carries a Retry-After header (1-60 seconds)"""
    r = api.login_raw("ravi", "Wrong-Password-7-xxxxx")
    assert r.status_code == 429
    ra = r.headers.get("retry-after", "")
    assert ra.isdigit() and 1 <= int(ra) <= 60, f"Retry-After={ra!r}"


@cat("AUTHN")
def test_authn_22_rate_limit_applies_to_valid_credentials(api):
    """AUTHN-22 While throttled even correct credentials get 429 (no token issued)"""
    r = api.login_raw("asha", USERS["asha"]["password"])
    assert r.status_code == 429
    assert "access_token" not in r.text
