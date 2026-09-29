"""Lab 7 Part A - call the transfer API from Python (same on Windows/macOS/Linux).
Pre-req: server running (fastapi dev main.py). Run: python client.py
"""
import time

import httpx2

BASE = "http://127.0.0.1:8000"

with httpx2.Client(base_url=BASE, timeout=10.0) as client:
    t0 = time.perf_counter()
    r = client.post("/transfers", json={"from_account": "ACC-101", "to_account": "ACC-102", "amount": 1500})
    print(r.status_code, r.json(), f"in {time.perf_counter() - t0:.3f}s")   # 202 in a few ms

    r = client.post("/transfers", json={"from_account": "ACC-103", "to_account": "ACC-101", "amount": 99999})
    print(r.status_code, r.json())                                              # 400 insufficient funds

    r = client.post("/transfers", json={"from_account": "ACC-101", "to_account": "ACC-102", "amount": -5})
    print(r.status_code, r.json()["detail"][0]["msg"])                          # 422 validation error

    print(client.get("/accounts/ACC-101").json())
