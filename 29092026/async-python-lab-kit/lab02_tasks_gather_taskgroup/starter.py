"""Lab 2 - Tasks, gather() and TaskGroup
Scenario: end-of-day reconciliation. Pull today's transaction count from 5 branches.
Branch delays differ; branch 'PUNE' is down and raises an error.

Run: python starter.py   (each TODO function raises NotImplementedError until you fill it)

TODO A  run_with_gather():     use asyncio.gather -> results in the SAME order as the input
TODO B  run_with_tasks():      use asyncio.create_task to START work immediately,
                               do other work (print "preparing report..."), then await the tasks
TODO C  run_with_taskgroup():  use 'async with asyncio.TaskGroup() as tg:' (Python 3.11+)
TODO D  run_tolerant():        include PUNE; use gather(..., return_exceptions=True)
                               and print which branches failed without crashing
"""
import asyncio
import time

START = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{time.perf_counter() - START:5.2f}s] {msg}")


DELAYS = {"GURGAON": 1.0, "NOIDA": 2.0, "DELHI": 0.5, "BENGALURU": 1.5, "PUNE": 0.8}
HEALTHY = ["GURGAON", "NOIDA", "DELHI", "BENGALURU"]


async def fetch_txn_count(branch: str) -> int:
    log(f"-> {branch}")
    await asyncio.sleep(DELAYS[branch])
    if branch == "PUNE":
        raise ConnectionError(f"{branch} branch server unreachable")
    log(f"<- {branch}")
    return len(branch) * 100  # fake number


async def run_with_gather() -> list[int]:
    raise NotImplementedError("TODO A")


async def run_with_tasks() -> list[int]:
    raise NotImplementedError("TODO B")


async def run_with_taskgroup() -> list[int]:
    raise NotImplementedError("TODO C")


async def run_tolerant() -> None:
    raise NotImplementedError("TODO D")


async def main() -> None:
    for step in (run_with_gather, run_with_tasks, run_with_taskgroup, run_tolerant):
        print(f"\n=== {step.__name__} ===")
        t0 = time.perf_counter()
        try:
            result = await step()
            if result is not None:
                print("result:", result)
        except NotImplementedError as exc:
            print("skipped:", exc)
        print(f"took {time.perf_counter() - t0:.2f}s (expected ~2.0s)")


if __name__ == "__main__":
    asyncio.run(main())
