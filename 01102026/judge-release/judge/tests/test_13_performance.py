"""Non-functional requirements: latency of single, sequential requests (local machine, generous budgets)."""
import statistics
import time

import pytest

from harness import USERS

cat = pytest.mark.cat


def p95(samples):
    return statistics.quantiles(samples, n=20)[18]


def timed(fn, n):
    out = []
    for _ in range(n):
        t = time.perf_counter()
        r = fn()
        out.append(time.perf_counter() - t)
        assert r.status_code < 500
    return out


@cat("RESILIENCE")
def test_nfr_01_list_latency(api):
    """NFR-01 GET /expenses (page_size=100, filters) p95 < 300 ms over 50 calls"""
    h = api.auth("farah")
    api.http.get("/api/v1/expenses", headers=h)                   # warm-up
    s = timed(lambda: api.http.get("/api/v1/expenses", headers=h,
                                   params={"page_size": "100", "q": "a", "sort": "-amount_paise"}), 50)
    assert p95(s) < 0.300, f"p95={p95(s) * 1000:.0f} ms"


@cat("RESILIENCE")
def test_nfr_02_decision_latency(api):
    """NFR-02 POST /decision p95 < 300 ms over 20 calls"""
    s = timed(lambda: api.decide("priya", 1003), 20)             # 409 path: full auth + lookup
    assert p95(s) < 0.300, f"p95={p95(s) * 1000:.0f} ms"


@cat("RESILIENCE")
def test_nfr_03_login_latency_bounded(api):
    """NFR-03 Login p95 < 1500 ms (slow hash, but usable) over 8 calls"""
    s = timed(lambda: api.login_raw("meera", USERS["meera"]["password"]), 8)
    assert p95(s) < 1.5, f"p95={p95(s) * 1000:.0f} ms"
