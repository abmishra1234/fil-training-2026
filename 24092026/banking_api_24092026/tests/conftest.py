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
import uuid

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DB = ROOT / "test_bank.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"   # env var beats .env
os.environ["JWT_SECRET_KEY"] = "test-secret-" + "x" * 48
os.environ["ADMIN_USERNAME"] = "test.admin"
os.environ["ADMIN_PASSWORD"] = "Test-Admin-Passphrase!"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app                   # noqa: E402

PASSWORD = "Correct-Horse-Battery-9"        # 15+ chars (NIST SP 800-63B-4)


def _token(c: TestClient, username: str, password: str) -> str:
    r = c.post("/api/v1/auth/token", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def anon_client():
    """No Authorization header at all."""
    with TestClient(app, raise_server_exceptions=False) as c:   # runs startup -> create_all + seed admin
        yield c
    if TEST_DB.exists():
        TEST_DB.unlink()


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
