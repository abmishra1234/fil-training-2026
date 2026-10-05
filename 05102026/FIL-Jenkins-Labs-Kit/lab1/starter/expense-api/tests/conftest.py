"""Shared test fixtures: build the app in-process (no server, no network)."""
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]

# Seed users we log in as (passwords come from seed/seed_data.json - lab data only)
ASHA = ("asha", "Monsoon-Chai-Walks-2026")       # EMPLOYEE, id 1
PRIYA = ("priya", "Tall-Mango-Tree-Shade-31")    # MANAGER,  id 4


def make_env(**overrides):
    env = {
        "APP_ENV": "test",
        "APP_PORT": "8000",
        "JWT_SECRET": secrets.token_urlsafe(48),
        "SEED_FILE": str(ROOT / "seed" / "seed_data.json"),
        "CORS_ALLOWED_ORIGINS": "https://expenses.example.com",
    }
    env.update(overrides)
    return env


@pytest.fixture()
def client():
    app = create_app(load_settings(make_env()))
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def login(client):
    def _login(user):
        r = client.post("/api/v1/auth/token", json={"username": user[0], "password": user[1]})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
