"""Lab 7 Part B - fire 5 concurrent requests at each slow endpoint.
Pre-req: server running (fastapi dev main.py). Run: python load_test.py
Before running, PREDICT the total time for each endpoint and write it down!
"""
import asyncio
import time

import httpx2

BASE = "http://127.0.0.1:8000"


async def hit(path: str, n: int = 5) -> None:
    async with httpx2.AsyncClient(base_url=BASE, timeout=30.0) as client:
        t0 = time.perf_counter()
        await asyncio.gather(*(client.get(path) for _ in range(n)))
        print(f"{path:<26} {n} parallel requests -> {time.perf_counter() - t0:4.1f}s")


async def main() -> None:
    for path in ("/slow/async-blocking", "/slow/sync-def", "/slow/async-nonblocking"):
        await hit(path)


if __name__ == "__main__":
    asyncio.run(main())
