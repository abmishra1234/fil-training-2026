"""Ext 6 - Task 3: get_current_user validates every token."""
import base64
import json
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def _me(c, token):
    return c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})


def _forge(**overrides):
    now = datetime.now(timezone.utc)
    claims = {"sub": "1", "role": "ADMIN", "iss": settings.JWT_ISSUER,
              "iat": now, "exp": now + timedelta(minutes=5)}
    claims.update(overrides)
    return claims


def test_me_returns_the_logged_in_user(anon_client, login):
    h = login("me.user")
    r = anon_client.get("/api/v1/auth/me", headers=h)
    assert r.status_code == 200
    assert r.json()["username"] == "me.user"
    assert "hashed_password" not in r.json()


def test_missing_token_is_401_with_standard_envelope(anon_client):
    r = anon_client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "Bearer"
    assert r.json()["error"]["code"] == "not_authenticated"
    assert "request_id" in r.json()["error"]


def test_garbage_token_is_401(anon_client):
    assert _me(anon_client, "not.a.jwt").status_code == 401


def test_tampered_payload_is_401(anon_client, login):
    token = login("tamper.user")["Authorization"].split()[1]
    header, payload, sig = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["role"] = "ADMIN"                                       # privilege escalation attempt
    evil = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    assert _me(anon_client, f"{header}.{evil}.{sig}").status_code == 401


def test_token_signed_with_another_key_is_401(anon_client):
    forged = jwt.encode(_forge(), "attacker-guessed-secret-" + "y" * 20, algorithm="HS256")
    assert _me(anon_client, forged).status_code == 401


def test_expired_token_is_401(anon_client):
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    expired = jwt.encode(_forge(iat=past, exp=past + timedelta(minutes=15)),
                         settings.JWT_SECRET_KEY, algorithm="HS256")
    assert _me(anon_client, expired).status_code == 401


def test_alg_none_token_is_401(anon_client):
    unsigned = jwt.encode(_forge(), key=None, algorithm="none")
    assert _me(anon_client, unsigned).status_code == 401


def test_wrong_issuer_is_401(anon_client):
    other = jwt.encode(_forge(iss="some-other-service"), settings.JWT_SECRET_KEY, algorithm="HS256")
    assert _me(anon_client, other).status_code == 401


def test_token_for_deleted_user_is_401(anon_client):
    ghost = jwt.encode(_forge(sub="987654"), settings.JWT_SECRET_KEY, algorithm="HS256")
    assert _me(anon_client, ghost).status_code == 401
