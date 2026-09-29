# Lab 7 - FastAPI Mini Bank: async endpoints + BackgroundTasks (45 min)

Terminal 1: `fastapi dev main.py`  -> open http://127.0.0.1:8000/docs
Terminal 2: `python client.py` then `python load_test.py`

## Part A - BackgroundTasks
1. POST /transfers in Swagger UI. Response is **202 Accepted** in milliseconds.
2. Watch terminal 1: `[bg] ... notifications sent` appears ~3 s *after* the response.
3. Try amount = -5 (422), an amount bigger than the balance (400), an unknown account (404).

## Part B - `def` vs `async def` (predict first!)
| Endpoint | 5 parallel requests | Why |
|---|---|---|
| `/slow/async-blocking` | ~5 s | `time.sleep` in `async def` blocks the single event loop |
| `/slow/sync-def` | ~1 s | plain `def` endpoints run in a thread pool |
| `/slow/async-nonblocking` | ~1 s | `await asyncio.sleep` yields to the loop |

Rule of thumb: use `async def` only if everything slow inside is awaited; otherwise use plain `def`.

BackgroundTasks limits: same process, lost if the process restarts, no retry, no status.
For guaranteed delivery use a queue + workers (Lab 8), and in production a broker
(Celery, RQ, Arq, Dramatiq with Redis/RabbitMQ, or Kafka/SQS).

No curl needed. On Windows PowerShell, `curl` is an alias of Invoke-WebRequest; use `curl.exe` or `client.py`.
