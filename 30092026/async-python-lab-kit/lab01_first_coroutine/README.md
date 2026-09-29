# Lab 1 - Your first coroutine (20 min)

**Goal:** feel the difference between blocking and non-blocking waits.

| Step | Do this | You should see |
|---|---|---|
| 1 | `python starter.py` | three requests one after another, total ~6 s |
| 2 | TODO 1-4: `async def`, `await asyncio.sleep`, `asyncio.run(main())` | still ~6 s (!) |
| 3 | TODO 6: `await asyncio.gather(...)` | all three `->` lines at 0.00 s, total ~2 s |
| 4 | Remove an `await` on purpose | `RuntimeWarning: coroutine 'fetch_balance' was never awaited` |

**Key idea:** `async def` only *allows* concurrency. You get it when you hand several
coroutines to the event loop at once (`gather`, `create_task`, `TaskGroup`).

Compare with `solution.py` only after you tried.
