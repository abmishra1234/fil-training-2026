# Async Python - Classroom Lab Kit

Hands-on kit for the **"Async Processing with Python"** training (FIL Gurgaon dev onboarding).
Every lab has a `README.md`, a `starter.py` with numbered TODOs and a working `solution.py`.
Read the matching slides, try the starter, peek at the solution only when you are stuck.

## 1. Setup (15 min, do it before class)

Requirements: **Python 3.11+ (3.13 recommended)**, VS Code (Python extension), a terminal.

**Windows (PowerShell)**
```powershell
cd async-python-lab-kit
py -3.13 -m venv .venv            # or: python -m venv .venv
.venv\Scripts\Activate.ps1        # blocked by policy? run:  .venv\Scripts\activate.bat  (in cmd)
python -m pip install -r requirements.txt
python 00_setup/verify_setup.py
```

**macOS / Linux**
```bash
cd async-python-lab-kit
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python 00_setup/verify_setup.py
```

Behind the corporate proxy? `pip install --proxy http://<proxy-host>:<port> -r requirements.txt`
or use the internal package mirror your team provides (`pip config set global.index-url <mirror-url>`).

## 2. Lab map

| # | Folder | Topic | Time |
|---|---|---|---|
| 0 | `00_setup` | verify environment | 15 min |
| 1 | `lab01_first_coroutine` | `async def`, `await`, `asyncio.run`, `gather` | 20 min |
| 2 | `lab02_tasks_gather_taskgroup` | `create_task`, `gather`, `TaskGroup`, partial failure | 30 min |
| 3 | `lab03_blocking_trap` | blocking calls, `to_thread`, process pool, debug mode | 25 min |
| 4 | `lab04_timeouts_retries_errors` | `asyncio.timeout`, retry + backoff, cancellation | 30 min |
| 5 | `lab05_queue_semaphore` | producer/consumer `Queue`, `Semaphore` rate limit | 30 min |
| 6 | `lab06_async_http` | `httpx2.AsyncClient` against a local mock bank API | 30 min |
| 7 | `lab07_fastapi_banking` | FastAPI async endpoints, `BackgroundTasks`, def vs async def | 45 min |
| 8 | `lab08_capstone` | queue + workers + lifespan + tests (pytest-asyncio) | 75 min |

Run every lab **from inside its folder**, e.g. `cd lab03_blocking_trap` then `python starter.py`.
Labs 6-8 need a server in a second terminal (see each README). Stop a server with `Ctrl+C`.

## 3. How to know you are done
* Labs 1-7: your output matches "Expected" in the lab README (timings within ~0.2 s).
* Lab 8: `pytest -v` in `lab08_capstone/starter` shows **11 passed**.

See `CHEATSHEET.md` and `TROUBLESHOOTING.md`.
