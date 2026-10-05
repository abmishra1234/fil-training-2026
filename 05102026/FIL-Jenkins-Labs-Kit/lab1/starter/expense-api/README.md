# Expense Claims API - Jenkins lab project

FastAPI service used in the FIL Jenkins labs. Python 3.11+.

| Command (run from this folder) | What it does |
|---|---|
| `python3 -m venv .venv && . .venv/bin/activate` | create + activate a virtual env (Windows: `.venv\Scripts\activate`) |
| `pip install -r requirements-dev.txt` | app + CI tools (ruff, pytest, httpx) |
| `ruff check app tests scripts` | **Lint** - must print `All checks passed!` |
| `pytest -q` | **Test** - must print `13 passed` |
| `pip wheel . --no-deps -w dist` | **Build** - creates `dist/expense_api-1.0.0-py3-none-any.whl` |
| `bash scripts/deploy_local.sh` | **Deploy** to `$HOME/staging/expense-api` (needs `JWT_SECRET`, Linux/macOS/Git-Bash) |
| `python scripts/smoke_test.py` | checks the deployed service on http://127.0.0.1:8000 |

Seed users and passwords in `seed/seed_data.json` are fake lab data.
