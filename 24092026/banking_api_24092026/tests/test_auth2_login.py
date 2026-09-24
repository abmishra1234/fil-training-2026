"""Ext 6 - Task 2: Login issues a JWT."""
import base64
import json

import jwt

PW = "Correct-Horse-Battery-9"


def _claims(token):
    # Anyone can read a JWT payload - no key needed. That's the point of this test.
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def test_login_returns_bearer_token(anon_client):
    anon_client.post("/api/v1/auth/register", json={"username": "login.ok", "password": PW})
    r = anon_client.post("/api/v1/auth/token", data={"username": "login.ok", "password": PW})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] > 0
    assert body["access_token"].count(".") == 2                   # header.payload.signature


def test_token_claims_are_minimal_and_correct(anon_client):
    anon_client.post("/api/v1/auth/register", json={"username": "claims.user", "password": PW})
    token = anon_client.post("/api/v1/auth/token",
                             data={"username": "claims.user", "password": PW}).json()["access_token"]
    header = jwt.get_unverified_header(token)
    claims = _claims(token)
    assert header["alg"] == "HS256"
    assert {"sub", "role", "iat", "exp", "iss"} <= set(claims)
    assert isinstance(claims["sub"], str)                         # PyJWT >= 2.10 rule
    assert claims["role"] == "CUSTOMER" and claims["iss"] == "bank_api"
    assert 0 < claims["exp"] - claims["iat"] <= 60 * 60           # short-lived (<= 1h)
    for forbidden in ("password", "balance", "account_number", "owner_name"):
        assert forbidden not in claims


def test_wrong_password_and_unknown_user_look_identical(anon_client):
    anon_client.post("/api/v1/auth/register", json={"username": "login.bad", "password": PW})
    wrong_pw = anon_client.post("/api/v1/auth/token", data={"username": "login.bad", "password": "nope-nope-nope-nope"})
    no_user = anon_client.post("/api/v1/auth/token", data={"username": "ghost.user", "password": PW})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json()["error"]["message"] == no_user.json()["error"]["message"]
    assert wrong_pw.headers.get("WWW-Authenticate") == "Bearer"


def test_login_expects_form_data_not_json(anon_client):
    r = anon_client.post("/api/v1/auth/token", json={"username": "x", "password": "y"})
    assert r.status_code == 422
