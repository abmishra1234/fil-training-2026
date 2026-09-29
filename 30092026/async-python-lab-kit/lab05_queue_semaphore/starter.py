"""Lab 5 - Producer/Consumer with asyncio.Queue + rate limiting with Semaphore
Scenario: 12 transfers just happened. Each needs an SMS notification (0.5 s each).
The SMS vendor allows at most 2 concurrent connections from us.

Run: python starter.py   -> today it sends one by one: ~6 s

TODO 1: create  queue: asyncio.Queue[Notification] = asyncio.Queue()
TODO 2: producer: put all 12 notifications on the queue (await queue.put(n))
TODO 3: worker(name): loop forever: n = await queue.get(); send it; queue.task_done()
        (put task_done in a 'finally' so a failure doesn't hang queue.join())
TODO 4: start 4 workers with asyncio.create_task, then  await queue.join()
TODO 5: after join(), cancel the workers (they are in an infinite loop)
TODO 6: the vendor limit! wrap the send in 'async with sms_limit:' where
        sms_limit = asyncio.Semaphore(2). Watch 'in-flight' never exceed 2.
Expected final result: ~3.0 s  (12 SMS / 2 concurrent * 0.5 s)
"""
import asyncio
import time
from dataclasses import dataclass

START = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{time.perf_counter() - START:5.2f}s] {msg}")


@dataclass
class Notification:
    transfer_id: int
    phone: str


in_flight = 0  # how many SMS are being sent right now


async def send_sms(n: Notification, worker: str) -> None:
    global in_flight
    in_flight += 1
    log(f"{worker} sending T{n.transfer_id:02d}  (in-flight={in_flight})")
    await asyncio.sleep(0.5)
    in_flight -= 1


async def main() -> None:
    notifications = [Notification(i, f"+91-98100-{i:05d}") for i in range(1, 13)]
    for n in notifications:  # sequential version - replace with queue + workers
        await send_sms(n, "main")
    log("all notifications sent")


if __name__ == "__main__":
    asyncio.run(main())
