# Lab 2 - Tasks, gather() and TaskGroup (30 min)

| Tool | Use it when | Failure behaviour |
|---|---|---|
| `asyncio.gather(*coros)` | you want all results, in order | first exception propagates; others keep running |
| `gather(..., return_exceptions=True)` | partial success is OK | exceptions come back as values |
| `asyncio.create_task(coro)` | start now, await later | you must keep a reference and await it |
| `asyncio.TaskGroup()` (3.11+) | default choice for new code | cancels siblings, raises `ExceptionGroup` |

Expected: A, B and C each take ~2.0 s (the slowest branch, NOIDA). D prints PUNE as FAILED.
Bonus in solution: `except* ConnectionError` with TaskGroup.
