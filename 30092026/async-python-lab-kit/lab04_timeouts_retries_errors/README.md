# Lab 4 - Timeouts, Retries, Cancellation (30 min)

Rules every production async service follows:

1. **Every network call has a timeout.** `async with asyncio.timeout(sec):` (3.11+).
2. **Retry only transient errors** (connection reset, 503), with **exponential backoff**.
   Pass a *factory* (`lambda: gateway.send(...)`) - a coroutine object can only be awaited once.
3. **Never swallow `asyncio.CancelledError`.** Clean up, then `raise`.

Expected output (solution): A prints TIMEOUT at ~1.0 s; B fails twice then succeeds on call 3;
C logs the cleanup message and "task reported as cancelled - correct!".
