hon -m # CabRoster — Student Starter Kit

Employee pickup (06:30) & drop (16:30) cab service backend. Read the spec
(`CabRoster_Requirements_and_Backlog.docx`) first — especially sections 2 (business rules),
5 (API conventions), 6 (endpoints) and Appendix A (Test Contract).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload      # http://127.0.0.1:8000/docs
```

## What is already done for you

| File | Status |
|---|---|
| `app/config.py`, `app/database.py`, `app/main.py` | Done |
| `app/models.py` | Enums + `User` done; **Cab, Trip, Booking are TODO** |
| `app/core/deps.py` | `get_now`, `PageParams` done; **auth dependencies TODO** |
| `app/core/security.py`, `app/core/query.py` | TODO |
| `app/schemas.py` | `Page`, `UserRead`, `Token` done; the rest TODO |
| `app/services/*` | TODO — business rules live here |
| `app/routers/*` | Every route, path and parameter is declared; bodies are TODO |
| `tests/simple/` | Basic test suite (38 tests), 1–2 checks per API |

Search for `TODO` and `NotImplementedError` to find your work. Each TODO names its backlog item (DEV-xx).

## Suggested order (matches the 2 h 30 min plan)

1. DEV-03 `core/security.py` + `core/deps.py`. Nothing else can pass until `hash_password` works.
2. DEV-04 register / login / me.
3. DEV-02 models, DEV-06 `core/query.py`.
4. DEV-07 users, DEV-08 cabs.
5. DEV-09…11 bookings (`services/rules.py`, `services/booking_service.py`).
6. DEV-12…15 trips & driver (`services/trip_service.py`, `services/mappers.py`).

## Running the tests

```bash
pytest                         # run everything in tests/
pytest -x                      # stop at the first failure
pytest -k booking              # only tests whose name contains "booking"
pytest tests/simple -v         # verbose list
```

Right now only `test_health` passes. Each passing test tells you a piece is wired correctly.
Your instructor has a much larger **full suite** that checks every business rule, boundary time and error code.
Passing the simple suite does **not** mean you will pass the full suite, so test the edge cases yourself too.

## Test Contract — do not break these

The tests plug into your code at exactly these points. Renaming them breaks the tests:

- `app.main.app` — the FastAPI instance; routers mounted under `/api/v1`
- `app.database.Base`, `app.database.SessionLocal`, `app.database.get_db`
- `app.core.deps.get_now` — **always** receive time as `now: datetime = Depends(get_now)`
- `app.core.security.hash_password(plain) -> str`
- `app.models.User` (columns exactly as spec 4.1) and `app.models.Role`
- `app.config.settings.JWT_SECRET_KEY` and `settings.JWT_ALGORITHM == "HS256"`
- JWT `exp` uses the real clock (`datetime.now(timezone.utc)`), never `get_now()`
- List ties are broken by `id` ascending
