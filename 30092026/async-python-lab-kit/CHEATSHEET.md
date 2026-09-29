# asyncio Cheat Sheet (Python 3.11+)

| I want to... | Code |
|---|---|
| define a coroutine | `async def fetch(): ...` |
| run the program | `asyncio.run(main())` (once, at the top) |
| wait for one thing | `result = await fetch()` |
| run N things, get results in order | `a, b = await asyncio.gather(f1(), f2())` |
| ...and keep going if some fail | `await asyncio.gather(*coros, return_exceptions=True)` |
| start now, collect later | `t = asyncio.create_task(f()); ...; r = await t` |
| structured concurrency (preferred) | `async with asyncio.TaskGroup() as tg: tg.create_task(f())` |
| handle TaskGroup errors | `except* ValueError as eg: eg.exceptions` |
| timeout | `async with asyncio.timeout(2): await f()` -> `TimeoutError` |
| non-blocking pause | `await asyncio.sleep(1)` (never `time.sleep` in async code) |
| call blocking I/O code | `await asyncio.to_thread(blocking_fn, arg)` |
| call CPU-heavy code | `await loop.run_in_executor(ProcessPoolExecutor(), fn, arg)` |
| limit concurrency | `sem = asyncio.Semaphore(5)`; `async with sem: ...` |
| protect shared state across awaits | `lock = asyncio.Lock()`; `async with lock: ...` |
| work queue | `q = asyncio.Queue(maxsize=100)`; `await q.put(x)`; `x = await q.get()`; `q.task_done()`; `await q.join()` |
| cancel | `t.cancel()`; inside: `except asyncio.CancelledError: cleanup(); raise` |
| HTTP | `async with httpx2.AsyncClient(timeout=5) as c: r = await c.get(url)` |
| debug slow steps | `asyncio.run(main(), debug=True)` or `PYTHONASYNCIODEBUG=1` |
| FastAPI after-response work | `background_tasks.add_task(fn, *args)` |
| FastAPI startup/shutdown | `FastAPI(lifespan=lifespan)` with `@asynccontextmanager` |
| async test | `async def test_x(): ...` with `asyncio_mode = auto` (pytest-asyncio) |

## Decision guide
* **I/O-bound** (HTTP, DB, files, queues) -> asyncio (or threads for legacy sync libs).
* **CPU-bound** (maths, image/PDF generation, ML inference in Python) -> processes.
* **Must survive restarts / needs guaranteed delivery** -> message broker + workers (Celery, RQ, Arq, Kafka, SQS).

## The 5 classic bugs
1. Forgot `await` -> `RuntimeWarning: coroutine ... was never awaited`.
2. Blocking call (`time.sleep`, `requests`, sync DB driver) inside `async def`.
3. `create_task()` without keeping a reference -> task may be garbage-collected mid-run.
4. Swallowing `CancelledError` -> shutdown hangs.
5. Check-then-act on shared state with an `await` in between -> race condition (use `asyncio.Lock`).
