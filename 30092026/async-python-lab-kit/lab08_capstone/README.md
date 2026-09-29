# Lab 8 - Capstone: Mini Bank with an async notification pipeline (75 min)

Everything from Labs 1-7 in one small, production-shaped service.

```
POST /transfers ──► Bank.transfer()  (asyncio.Lock, no overdraft)
      │                    │
      │ 202 Accepted       └─► queue.put(transfer_id)
      ▼                                 │
GET /transfers/{id}          worker-0..N (started in lifespan)
  QUEUED → SENDING →           └─► notify(): email + SMS in parallel
  SENT / PARTIAL_FAILURE             (timeout + retry with backoff)
```

## How to work
```
cd lab08_capstone/starter
pytest -v            # 8 tests fail - your job is to make them all green
fastapi dev app/main.py   # try it in Swagger UI: http://127.0.0.1:8000/docs
```

| TODO | File | Makes these tests pass |
|---|---|---|
| 1 Lock the read-check-write | `app/bank.py` | `test_no_overdraft_under_concurrency` |
| 2 `with_retry` (timeout + backoff) | `app/notifier.py` | `test_retry_*` |
| 3 `notify` in parallel with `gather` | `app/notifier.py` | `test_notify_*` |
| 4 worker loop | `app/main.py` | `test_api.py` |
| 5 start workers in `lifespan` | `app/main.py` | `test_api.py` |

Suggested order: 1 → 2 → 3 → 5 → 4. Run `pytest -v -x` after each TODO.
Reference implementation: `../solution` (11 tests pass).

## Try it manually (solution or finished starter)
1. POST /transfers `{"from_account":"ACC-101","to_account":"ACC-102","amount":1500}` → 202 + `status_url`
2. GET the `status_url` twice quickly → `SENDING`, then `SENT`
3. POST from `ACC-103` (its phone is INVALID) → final status `PARTIAL_FAILURE` (email SENT, SMS FAILED)
4. GET /health → queue depth

## Stretch goals
* Add `GET /transfers` listing the last 20 transfers.
* Make worker count and delay configurable: `NOTIFY_WORKERS=5 NOTIFY_DELAY=2 fastapi dev app/main.py`
* Python 3.13+: replace worker cancellation with `queue.shutdown()`.
* Replace the in-memory queue with Redis + Arq / Celery and discuss what you gain (durability, retries across restarts).
