"""Lab 4 - Timeouts, Retries, Cancellation
Scenario: the external SMS gateway is unreliable.
  * sometimes it hangs for 5 s   -> we must give up after 1 s   (timeout)
  * sometimes it fails randomly  -> we must retry with backoff  (retry)
  * on shutdown, in-flight sends must clean up                  (cancellation)

Run: python starter.py

TODO A  send_with_timeout(): wrap the call in  'async with asyncio.timeout(1.0):'
        and catch TimeoutError -> return "TIMEOUT"
TODO B  with_retry(): call make_call() up to 'attempts' times; on ConnectionError
        wait base_delay * 2**(attempt-1) seconds, then try again; re-raise on last attempt
TODO C  cancellable_send(): catch asyncio.CancelledError, log "cleanup", then RE-RAISE it
"""
import asyncio
import time
from collections.abc import Awaitable, Callable

START = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{time.perf_counter() - START:5.2f}s] {msg}")


async def hanging_gateway(phone: str) -> str:
    await asyncio.sleep(5)  # the gateway hangs
    return f"sent to {phone}"


class FlakyGateway:
    """Fails the first `failures` calls, then succeeds (deterministic for class)."""

    def __init__(self, failures: int = 2) -> None:
        self.failures = failures
        self.calls = 0

    async def send(self, phone: str) -> str:
        self.calls += 1
        await asyncio.sleep(0.1)
        if self.calls <= self.failures:
            raise ConnectionError(f"gateway error on call {self.calls}")
        return f"sent to {phone} on call {self.calls}"


async def send_with_timeout(phone: str) -> str:
    raise NotImplementedError("TODO A")


async def with_retry(make_call: Callable[[], Awaitable[str]], attempts: int = 3, base_delay: float = 0.2) -> str:
    raise NotImplementedError("TODO B")


async def cancellable_send(phone: str) -> None:
    raise NotImplementedError("TODO C")


async def main() -> None:
    print("=== A timeout ===")
    try:
        log(f"result: {await send_with_timeout('+91-98100-00001')}")  # expect TIMEOUT after ~1 s
    except NotImplementedError as exc:
        print("skipped:", exc)

    print("\n=== B retry ===")
    gateway = FlakyGateway(failures=2)
    try:
        log(f"result: {await with_retry(lambda: gateway.send('+91-98100-00002'))}")  # succeeds on call 3
    except NotImplementedError as exc:
        print("skipped:", exc)

    print("\n=== C cancellation ===")
    task = asyncio.create_task(cancellable_send("+91-98100-00003"))
    await asyncio.sleep(0.5)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        log("task reported as cancelled - correct!")
    except NotImplementedError as exc:
        print("skipped:", exc)


if __name__ == "__main__":
    asyncio.run(main())
