# Lab 5 - Queue + Semaphore (30 min)

* `asyncio.Queue` decouples **who creates work** (producer: the transfer API) from
  **who does it** (workers: notification senders). This is the in-process version of Kafka/RabbitMQ/SQS.
* `asyncio.Semaphore(n)` caps concurrency: protects vendors, DB pools and rate limits.

Checklist: `task_done()` in `finally` / `await queue.join()` / cancel workers afterwards /
bounded queue (`maxsize`) gives back-pressure.

Expected (solution): in-flight never exceeds 2; total ~3.0 s.
Try: Semaphore(4) -> ~1.5 s. Semaphore(1) -> ~6 s. Workers=1 -> ~6 s regardless of semaphore.
Python 3.13+ also offers `queue.shutdown()` for graceful stop.
