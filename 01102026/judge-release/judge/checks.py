"""Shared assertions."""
LEAK_MARKERS = ("Traceback", "Exception", 'File "', ".py\"", ".java", "java.", "at org.", "System.",
                "SQLException", "sqlite", "psycopg", "stack trace", "NullPointer", "KeyError",
                "TypeError", "ValueError", "pydantic", "hibernate")


def assert_envelope(r, status: int, code: str | None = None):
    assert r.status_code == status, f"expected {status}, got {r.status_code}: {r.text[:300]}"
    try:
        body = r.json()
    except ValueError:
        raise AssertionError(f"error body is not JSON: {r.text[:200]}")
    assert isinstance(body, dict) and isinstance(body.get("error"), dict), f"missing error envelope: {body}"
    err = body["error"]
    for k in ("code", "message", "correlation_id"):
        assert isinstance(err.get(k), str) and err[k], f"error.{k} missing/empty: {err}"
    if code:
        assert err["code"] == code, f"expected error.code={code}, got {err['code']}"
    assert err["correlation_id"] == r.headers.get("x-request-id"), \
        "error.correlation_id must equal the X-Request-ID response header"
    return err


def assert_no_leak(r):
    text = r.text
    for m in LEAK_MARKERS:
        assert m.lower() not in text.lower(), f"response leaks internals ({m!r}): {text[:300]}"


def assert_not_5xx(r):
    assert r.status_code < 500, f"server error {r.status_code}: {r.text[:300]}"
