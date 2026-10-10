# Expense API — Docker lab app (FIL Fresher Training)

A small FastAPI service that records expenses in SQLite. The lab packages it into a Docker image one Dockerfile move at a time.

## Endpoints
| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Liveness check, used by the Docker HEALTHCHECK |
| POST | `/expenses` | Add an expense: `{"title", "amount" > 0, "category", "spent_on"}` |
| GET | `/expenses?category=food` | List expenses, optional filter |
| GET | `/expenses/{id}` | One expense (404 if missing) |
| DELETE | `/expenses/{id}` | Delete one expense |
| GET | `/expenses/summary` | Count, total and total per category |

Categories: `food`, `travel`, `bills`, `shopping`, `other`. Swagger UI: `/docs`.

## Run without Docker (sanity check)
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload       # http://127.0.0.1:8000/docs
```

## Build and run with Docker
```bash
docker build -t expense-api:1.0 .
docker run -d --name expense -p 8000:8000 -v expense-data:/app/data expense-api:1.0
curl http://localhost:8000/health   # Windows PowerShell: curl.exe
```

## Building inside FIL (restricted network)
Docker Hub and pypi.org are blocked. Set the approved Harbor image and PyPI proxy once per terminal, then add `$FIL_ARGS` to every `docker build`:

```bash
# bash / Git Bash / WSL
FIL_ARGS="--build-arg BASE_IMAGE=<FIL-HARBOR>/<project>/python:3.13-slim
          --build-arg PIP_INDEX_URL=https://<FIL-PYPI-PROXY>/simple"
docker build $FIL_ARGS -t expense-api:1.0 .
```

```powershell
# PowerShell
$FIL_ARGS = "--build-arg", "BASE_IMAGE=<FIL-HARBOR>/<project>/python:3.13-slim",
            "--build-arg", "PIP_INDEX_URL=https://<FIL-PYPI-PROXY>/simple"
docker build $FIL_ARGS -t expense-api:1.0 .
```

- Harbor says `unauthorized`: run `docker login <FIL-HARBOR>` once. Never put passwords or tokens in the Dockerfile or in build args; `docker history` shows them.
- `SSL: CERTIFICATE_VERIFY_FAILED`: ask FIL IT for the root CA. Do not use `pip --trusted-host`.
- No venv inside the image: each `RUN` is a new shell, so `source .venv/bin/activate` does nothing for later lines (and `/bin/sh` has no `source`). The container already isolates the app.
- Push images to your Harbor project, not Docker Hub: `docker tag expense-api:1.0 <FIL-HARBOR>/<project>/expense-api:1.0`, then `docker push` that tag.

The database lives at `/app/data/expenses.db` (set by `EXPENSE_DB_PATH`), on the `expense-data` volume, so it survives `docker rm`.
