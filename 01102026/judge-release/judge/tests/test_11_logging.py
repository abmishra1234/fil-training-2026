"""A09 Security Logging & Alerting: structured JSON events on stdout, no secrets."""
import time

import pytest

from harness import USERS

cat = pytest.mark.cat
WRONG_PW = "Wrong-Password-For-Log-Test-7"


@pytest.fixture(scope="module")
def activity(api, app):
    """Drive one of every security-relevant action, then hand the log to the tests."""
    info = {}
    ok = api.login_raw("asha", USERS["asha"]["password"])
    info["token"] = ok.json()["access_token"]
    bad = api.login_raw("ravi", WRONG_PW, headers={"X-Request-ID": "judge-log-req-0001"})
    info["bad_login_rid"] = bad.headers.get("x-request-id")
    for _ in range(5):
        api.login_raw("kiran", WRONG_PW)
    api.http.get("/api/v1/expenses", headers={"Authorization": "Bearer forged.token.value"})
    api.decide("asha", 1007)                       # 403 role
    api.decide("priya", 1013)                      # 404 not visible
    api.decide("priya", 1017)                      # 403 self approval
    key = "judge-log-idem-0001"
    api.decide("priya", 1001, key=key)             # 200 decided
    api.decide("priya", 1001, key=key)             # replay (must not log a 2nd decision)
    info["tokens"] = [info["token"], api.token("priya"), api.token("farah")]
    time.sleep(1.0)
    info["events"] = app.log_events()
    info["text"] = app.log_text()
    return info


def find(events, name, **match):
    return [e for e in events if e.get("event") == name and all(str(e.get(k)) == str(v) for k, v in match.items())]


@cat("LOGGING")
def test_log_01_structured_json_lines(activity):
    """LOG-01 Security events are JSON lines with ts, level, event and request_id"""
    evs = activity["events"]
    assert len(evs) >= 8, f"only {len(evs)} JSON events found on stdout"
    for e in evs:
        for k in ("ts", "level", "event", "request_id"):
            assert k in e, f"event missing '{k}': {e}"


@cat("LOGGING")
def test_log_02_login_success(activity):
    """LOG-02 login_success is logged"""
    assert find(activity["events"], "login_success")


@cat("LOGGING")
def test_log_03_login_failed_with_request_id(activity):
    """LOG-03 login_failed is logged with the username and the request's X-Request-ID"""
    hits = find(activity["events"], "login_failed", username="ravi")
    assert hits, "no login_failed event for ravi"
    assert any(h.get("request_id") == activity["bad_login_rid"] for h in hits), \
        "login_failed event must carry the same request_id as the X-Request-ID response header"


@cat("LOGGING")
def test_log_04_account_locked(activity):
    """LOG-04 account_locked is logged when the lockout threshold is hit"""
    assert find(activity["events"], "account_locked", username="kiran")


@cat("LOGGING")
def test_log_05_auth_failed(activity):
    """LOG-05 auth_failed is logged for an invalid bearer token"""
    assert find(activity["events"], "auth_failed")


@cat("LOGGING")
def test_log_06_access_denied(activity):
    """LOG-06 access_denied is logged for role (403), visibility (404) and self-approval denials"""
    assert len(find(activity["events"], "access_denied")) >= 3


@cat("LOGGING")
def test_log_07_expense_decided_once(activity):
    """LOG-07 expense_decided logged once with expense_id, from_status, to_status (replay not re-logged)"""
    hits = [e for e in find(activity["events"], "expense_decided") if str(e.get("expense_id")) == "1001"]
    assert len(hits) == 1, f"expected exactly one expense_decided for 1001, got {len(hits)}"
    assert hits[0].get("from_status") == "SUBMITTED" and hits[0].get("to_status") == "APPROVED"


@cat("LOGGING")
def test_log_08_no_passwords_in_logs(activity):
    """LOG-08 No password (correct or attempted) ever appears in the logs"""
    text = activity["text"]
    assert WRONG_PW not in text
    for u in USERS.values():
        assert u["password"] not in text, f"password of {u['username']} found in logs"


@cat("LOGGING")
def test_log_09_no_tokens_or_secret_in_logs(activity, app):
    """LOG-09 No access token, token signature or JWT_SECRET appears in the logs"""
    text = activity["text"]
    assert app.secret not in text
    for t in activity["tokens"]:
        assert t not in text and t.split(".")[2] not in text
    assert "forged.token.value" not in text
