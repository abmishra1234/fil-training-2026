"""Lab 6 - baseline: SYNC client. Run (mock server must be running): python client_sync.py"""
import time

import httpx2

BASE = "http://127.0.0.1:8001"
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "SGD", "AED"]


def main() -> None:
    t0 = time.perf_counter()
    with httpx2.Client(base_url=BASE, timeout=5.0) as client:
        for ccy in CURRENCIES:
            data = client.get(f"/fx/{ccy}").raise_for_status().json()
            print(f"{data['currency']}: {data['inr']}")
    print(f"sync total: {time.perf_counter() - t0:.2f}s  (expected ~6 s)")


if __name__ == "__main__":
    main()
