## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for Swagger UI.

# bank_api – Extension 6 Reference Solution (Authentication & Authorization)

    pip install -r requirements.txt
    uvicorn app.main:app --reload       # http://127.0.0.1:8000/docs  -> "Authorize" button
    pytest -v                           # 108 passed (51 from Ext 5 + 57 new)

> Existing `bank.db` from Extension 5? Delete it once (dev only) – `create_all` never adds
> new columns (`accounts.owner_id`) to an existing table. In production you would write an
> Alembic migration instead.

## What changed
| Task | Files | Result |
|---|---|---|
| 1 Users & hashing | models/user.py, schemas/auth_schema.py, core/security.py, repositories/user_repository.py, services/auth_service.py | POST /api/v1/auth/register -> 201, Argon2id hash, role forced to CUSTOMER |
| 2 Login -> JWT | core/security.py, routers/auth_router.py | POST /api/v1/auth/token (form data) -> {access_token, token_type, expires_in} |
| 3 Who is calling? | core/auth.py `get_current_user` | Signature, alg, exp, iss checked; user re-loaded from DB; GET /api/v1/auth/me |
| 4 Lock the doors | routers/*.py (router-level `dependencies=[...]`) | Every money route (v1 AND legacy) -> 401 without a token |
| 5 Ownership (BOLA) | models/account.py `owner_id`, core/auth.py `AccountAccess` | View = owner/admin, Operate = owner only, others -> 404; idempotency keys per user |
| 6 Roles (RBAC) | core/auth.py `require_role`, routers/admin_router.py, account_router.py | KYC update ADMIN-only, admin sees all accounts, admin can disable users |

## Default admin (dev)
`bank.admin` / `Admin-Passphrase-2026!` – set in `.env`, created at startup.

## Windows / Anaconda startup
Run these commands from the directory containing `app` and `requirements.txt` (the project root):

```powershell
conda activate <your-environment>
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The import path is `app.main:app`; `app.main` must be importable from the project root. If you launch Uvicorn from another directory, first run `Set-Location` to this directory or pass `--app-dir` with this project's path. Using `python -m pip` and `python -m uvicorn` ensures dependencies and the server come from the same active Python environment.
