"""Lab 1 - Your first coroutine: Sync vs Async
Scenario: the mobile banking dashboard needs balances of 3 accounts.
Each call to the core-banking system takes ~2 seconds (network I/O).

Run:  python starter.py      -> takes ~6 s  (one after another)
Goal: make it take ~2 s      -> all three waits overlap

TODO 1: import asyncio
TODO 2: turn fetch_balance into a coroutine   (def -> async def)
TODO 3: replace time.sleep(delay) with  await asyncio.sleep(delay)
TODO 4: turn main into a coroutine and start it with asyncio.run(main())
TODO 5: run it -> still ~6 s?  (yes! awaiting one-by-one is still sequential)
TODO 6: use asyncio.gather(...) to run the 3 calls concurrently -> ~2 s
"""
import time

START = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{time.perf_counter() - START:5.2f}s] {msg}")


BALANCES = {"ACC-101": 5_000, "ACC-102": 12_000, "ACC-103": 800}


def fetch_balance(account: str, delay: float = 2.0) -> int:
    log(f"-> requesting balance for {account}")
    time.sleep(delay)  # simulates waiting for the core-banking API
    log(f"<- received balance for {account}")
    return BALANCES[account]


def main() -> None:
    b1 = fetch_balance("ACC-101")
    b2 = fetch_balance("ACC-102")
    b3 = fetch_balance("ACC-103")
    log(f"Total balance = {b1 + b2 + b3}")


if __name__ == "__main__":
    main()
