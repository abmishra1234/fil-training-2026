"""API 1: POST /api/v1/auth/token"""
from tests.conftest import ASHA

URL = "/api/v1/auth/token"


def test_login_success_returns_bearer_token(client):
    r = client.post(URL, json={"username": ASHA[0], "password": ASHA[1]})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]


def test_wrong_password_gets_generic_401(client):
    r = client.post(URL, json={"username": ASHA[0], "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


def test_unknown_user_gets_same_generic_401(client):
    r = client.post(URL, json={"username": "nobody", "password": "whatever"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


def test_unknown_field_is_rejected(client):
    r = client.post(URL, json={"username": ASHA[0], "password": ASHA[1], "role": "ADMIN"})
    assert r.status_code == 400
