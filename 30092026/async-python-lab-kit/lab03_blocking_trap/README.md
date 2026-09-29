# Lab 3 - The Blocking Trap (25 min)

The #1 async bug in real projects: calling something blocking inside `async def`.

| Blocking (don't, inside async def) | Non-blocking replacement |
|---|---|
| `time.sleep(x)` | `await asyncio.sleep(x)` |
| `requests.get(url)` | `await httpx2.AsyncClient().get(url)` |
| sync DB driver / legacy SDK | async driver, or `await asyncio.to_thread(fn, ...)` |
| heavy CPU loop | `await loop.run_in_executor(ProcessPoolExecutor(), fn, ...)` |

Expected in `starter.py`: ticks stop for 3 s. In `solution.py`: ticks never stop.
Debug tip: `asyncio.run(main(), debug=True)` or env var `PYTHONASYNCIODEBUG=1`
prints a warning for any step that holds the loop for more than 100 ms.
