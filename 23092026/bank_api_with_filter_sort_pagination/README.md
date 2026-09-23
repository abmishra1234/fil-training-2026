# FastAPI Fundamentals — Personal Banking API

Clean layered architecture with **Routers → Services → Repositories**, **SQLAlchemy ORM**, and **Pydantic Settings**.

## Features
- Create account
- Get account by ID
- List all accounts
- Deposit money
- Withdraw money (insufficient funds check)
- Transfer money between accounts
- Store successful transfers in a transfer-history audit table
- Read and update KYC compliance status

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for Swagger UI.

## API versions

Every endpoint is available through both the current path and the versioned `/api/v1` path. Both paths use the same implementation and database.

| Current path | Versioned path |
| --- | --- |
| `/accounts/` | `/api/v1/accounts/` |
| `/accounts/transfer` | `/api/v1/accounts/transfer` |
| `/accounts/transfers` | `/api/v1/accounts/transfers` |
| `/accounts/{account_id}/deposit` | `/api/v1/accounts/{account_id}/deposit` |
| `/accounts/{account_id}/withdraw` | `/api/v1/accounts/{account_id}/withdraw` |
| `/accounts/{account_id}/kyc-status` | `/api/v1/accounts/{account_id}/kyc-status` |

See [the transfer-history manual test guide](docs/transfer_history_manual_testing.md) for filtering, sorting, and pagination examples.

## Run the tests

The API test suite uses a separate temporary SQLite database for every test, so it does not modify `bank.db`.

Install dependencies, then run the full suite:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

On macOS/Linux, activate the virtual environment with `source .venv/bin/activate` before running the same commands.

Useful commands:

```bash
# Show each test name and outcome
pytest -v

# Run only the API tests
pytest tests/test_api.py

# Run one test by name
pytest tests/test_api.py -k transfer

# Run the suite with terminal coverage for the application code
pytest --cov=app --cov-report=term-missing

# Generate an HTML coverage report, then open htmlcov/index.html in a browser
pytest --cov=app --cov-report=html
```

The suite covers successful and error responses for every endpoint, including validation (`422`), missing accounts (`404`), invalid money operations (`400`), transfers, and all KYC input styles. The coverage command measures the `app` package and displays any untested lines; the HTML report gives the same results in a browsable format.

### Persist 1,000 verification transfers in `bank.db`

The normal suite uses temporary databases and never changes `bank.db`. To deliberately create retained verification data, run the opt-in `bank_db` test below. It transfers 1 unit 1,000 times from existing account ID `1` to account ID `2`, creating 1,000 `transfer_history` rows in the database configured by `DATABASE_URL`. Account ID `1` must have a balance of at least 1,000.

```powershell
$env:RUN_BANK_DB_TESTS = "1"
pytest -m bank_db -v -s
Remove-Item Env:RUN_BANK_DB_TESTS
```

Do not run this command against a production database. The created records are intentionally retained for later verification.

## Dependency security audit

`pip-audit` is included in `requirements.txt` with the developer test tools. It checks the installed Python packages against the Python Packaging Advisory Database for known vulnerabilities.

```bash
# Install or update all project and audit dependencies
pip install -r requirements.txt

# Audit the packages installed in the active virtual environment
pip-audit

# Audit exactly the packages pinned in requirements.txt
pip-audit -r requirements.txt
```

Run the audit after changing a dependency and before releasing the API. A successful audit prints `No known vulnerabilities found` and exits with code `0`; any reported package should be updated or replaced before release.
