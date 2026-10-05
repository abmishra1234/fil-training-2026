"""Smoke test for a DEPLOYED Expense API (standard library only - no pip install needed).

Usage:  python scripts/smoke_test.py [--base-url http://127.0.0.1:8000] [--wait 30]
Exit code 0 = healthy, 1 = not healthy.  Prints a short PASS/FAIL report.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

# Lab-only seed user (see seed/seed_data.json). Never put real credentials in code.
USER, PASSWORD = "asha", "Monsoon-Chai-Walks-2026"


def call(method, url, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {}


def wait_until_up(base, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            call("GET", f"{base}/api/v1/expenses")   # any HTTP answer (even 401) = server is up
            return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(1)
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--wait", type=int, default=30, help="seconds to wait for the service to start")
    a = p.parse_args()
    base = a.base_url.rstrip("/")

    checks = []
    up = wait_until_up(base, a.wait)
    checks.append(("service is listening", up))
    if up:
        status, _ = call("GET", f"{base}/api/v1/expenses")
        checks.append(("GET /expenses without token -> 401", status == 401))
        status, body = call("POST", f"{base}/api/v1/auth/token", {"username": USER, "password": PASSWORD})
        token = body.get("access_token")
        checks.append(("POST /auth/token -> 200 + token", status == 200 and bool(token)))
        status, body = call("GET", f"{base}/api/v1/expenses", token=token)
        checks.append(("GET /expenses with token -> 200", status == 200 and "items" in body))

    for name, ok in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    ok = all(c[1] for c in checks)
    print("SMOKE TEST PASSED" if ok else "SMOKE TEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
