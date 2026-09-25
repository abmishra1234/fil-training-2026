"""Shared fixtures for the acceptance tests (Extensions 5 + 6).

Uses a throw-away SQLite file so your real bank.db is never touched.
Run from the project root:   pytest -v

Extension 6 changes:
  * `client` is now LOGGED IN as a default customer, so every Extension 5 test
    keeps working unchanged (all its accounts belong to that customer).
  * `anon_client` sends NO token - use it to prove the doors are locked.
  * `login(username)` registers + logs in any user and returns auth headers.
  * `admin_headers` is a token for the bootstrap ADMIN.
"""
import os
import pathlib
import sys
import tempfile
import uuid

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Use a unique database for each pytest process so concurrent student runs do
# not contend for a shared SQLite file. Delete it at session teardown below.
TEST_DB = pathlib.Path(tempfile.gettempdir()) / f"bank_api_test_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"   # env var beats .env
os.environ["JWT_SECRET_KEY"] = "test-secret-" + "x" * 48
os.environ["ADMIN_USERNAME"] = "test.admin"
os.environ["ADMIN_PASSWORD"] = "Test-Admin-Passphrase!"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app                   # noqa: E402
from app.database import engine             # noqa: E402

PASSWORD = "Correct-Horse-Battery-9"        # 15+ chars (NIST SP 800-63B-4)


def _token(c: TestClient, username: str, password: str) -> str:
    r = c.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def anon_client():
    """No Authorization header at all."""
    try:
        with TestClient(app, raise_server_exceptions=False) as c:  # startup -> create_all + seed admin
            yield c
    finally:
        # Ensure the app and pooled connections are closed before deleting the
        # SQLite file. Windows refuses to unlink a file that still has handles.
        engine.dispose()
        if TEST_DB.exists():
            try:
                TEST_DB.unlink()
            except PermissionError as exc:
                raise RuntimeError(
                    f"Could not remove test database {TEST_DB}; another process "
                    "may still be using it. Close duplicate pytest/uvicorn runs "
                    "and remove the file manually if needed."
                ) from exc


@pytest.fixture(scope="session")
def login(anon_client):
    """login('asha') -> {'Authorization': 'Bearer ...'}  (registers the user first if needed)."""
    def _login(username=None, password=PASSWORD):
        username = username or f"user_{uuid.uuid4().hex[:8]}"
        anon_client.post("/api/v1/auth/register",
                         json={"username": username, "password": password})
        return {"Authorization": f"Bearer {_token(anon_client, username, password)}"}
    return _login


@pytest.fixture(scope="session")
def admin_headers(anon_client):
    return {"Authorization": f"Bearer {_token(anon_client, 'test.admin', 'Test-Admin-Passphrase!')}"}


@pytest.fixture(scope="session")
def client(anon_client, login):
    """A client that is logged in as the default customer on EVERY request."""
    with TestClient(app, raise_server_exceptions=False) as c:
        c.headers.update(login("default.customer"))
        yield c


@pytest.fixture
def make_account(client, admin_headers):
    """make_account('Asha', balance=500, kyc=True, headers=None) -> account id
    Owned by the default customer unless you pass another user's headers."""
    def _make(owner="Test User", balance=0.0, kyc=False, headers=None):
        h = headers or {}
        r = client.post("/api/v1/accounts/", json={"owner_name": owner}, headers=h)
        assert r.status_code in (200, 201), r.text
        acc_id = r.json()["id"]
        if balance:
            client.post(f"/api/v1/accounts/{acc_id}/deposit", json={"amount": balance}, headers=h)
        if kyc:   # Ext 6: only an ADMIN may certify KYC
            r = client.put(f"/api/v1/accounts/{acc_id}/kyc-status",
                           json={"kyc_compliant": True}, headers=admin_headers)
            assert r.status_code == 200, r.text
        return acc_id
    return _make
