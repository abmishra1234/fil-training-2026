# FastAPI Fundamentals — Personal Banking API

Clean layered architecture with **Routers → Services → Repositories**, **SQLAlchemy ORM**, and **Pydantic Settings**.

## Features
- Create account
- Get account by ID
- List all accounts
- Deposit money
- Withdraw money (insufficient funds check)

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for Swagger UI.
