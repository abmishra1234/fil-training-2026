"""Lab 3 - The Blocking Trap
Scenario: while the server generates a customer's PDF statement, a heartbeat
task must keep printing 'tick' every 0.5 s (think: other users' requests).

Run: python starter.py
Observe: the ticks STOP for ~3 s. One blocking call froze the whole event loop.

TODO 1: run again with the debug flag:  asyncio.run(main(), debug=True)
        -> asyncio logs 'Executing <Task ...> took 3.0xx seconds'
TODO 2: fix render_pdf_bad: offload the blocking function with
        await asyncio.to_thread(blocking_render, customer)
TODO 3: CPU-heavy work (compute_interest) also blocks. Offload it to a
        ProcessPoolExecutor via loop.run_in_executor(pool, func, arg)
        (threads do not speed up CPU-bound Python code because of the GIL)
"""
import asyncio
import time

START = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{time.perf_counter() - START:5.2f}s] {msg}")


async def heartbeat() -> None:
    while True:
        log("tick")
        await asyncio.sleep(0.5)


def blocking_render(customer: str) -> str:
    time.sleep(3)  # e.g. a legacy PDF library or 'requests.get' - blocks the thread
    return f"statement_{customer}.pdf"


async def render_pdf_bad(customer: str) -> str:
    log("PDF: start")
    path = blocking_render(customer)  # BUG: blocking call inside async def
    log(f"PDF: done -> {path}")
    return path


def compute_interest(n: int) -> int:
    """CPU-bound: pure Python number crunching."""
    return sum(i * i % 7 for i in range(n))


async def main() -> None:
    hb = asyncio.create_task(heartbeat())
    await asyncio.sleep(1)
    await render_pdf_bad("CUST-42")
    await asyncio.sleep(1)
    hb.cancel()


if __name__ == "__main__":
    asyncio.run(main())
