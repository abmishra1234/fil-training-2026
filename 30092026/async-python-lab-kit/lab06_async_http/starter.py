"""Lab 6 - Async HTTP with httpx2.AsyncClient
Pre-req: mock server running ->  fastapi dev mock_bank_api.py --port 8001
First run the baseline:  python client_sync.py   (~6 s)

TODO 1: open ONE shared client:  async with httpx2.AsyncClient(base_url=BASE, timeout=5.0) as client:
TODO 2: write  async def get_rate(client, ccy) -> dict  using  await client.get(...)
TODO 3: fetch all 6 currencies concurrently with asyncio.gather  -> ~1 s
TODO 4: limit to 3 concurrent requests with asyncio.Semaphore(3) -> ~2 s  (be polite to partners!)
TODO 5: call get_rate for "XYZ" -> handle httpx2.HTTPStatusError (404) gracefully
"""
import asyncio
import time

import httpx2  # noqa: F401  (you will use it)

BASE = "http://127.0.0.1:8001"
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "SGD", "AED"]


async def main() -> None:
    t0 = time.perf_counter()
    # your code here
    print(f"async total: {time.perf_counter() - t0:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
