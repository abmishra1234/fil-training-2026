"""Ext 6 - Task 1: Users & safe password storage."""
import uuid

from app.core.security import hash_password, verify_password
from app.database import SessionLocal
from app.models.user import User

PW = "Correct-Horse-Battery-9"


def _name():
    return f"u_{uuid.uuid4().hex[:8]}"


def test_register_returns_201_and_customer_role(anon_client):
    name = _name()
    r = anon_client.post("/api/v1/auth/register", json={"username": name, "password": PW})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == name and body["role"] == "CUSTOMER" and body["is_active"] is True


def test_response_never_contains_the_password_or_hash(anon_client):
    r = anon_client.post("/api/v1/auth/register", json={"username": _name(), "password": PW})
    text = r.text.lower()
    assert "password" not in text and PW.lower() not in text


def test_password_is_stored_hashed_not_plain(anon_client):
    name = _name()
    anon_client.post("/api/v1/auth/register", json={"username": name, "password": PW})
    with SessionLocal() as db:
        stored = db.query(User).filter(User.username == name).one().hashed_password
    assert stored != PW and stored.startswith("$argon2")    # salted Argon2id hash
    assert verify_password(PW, stored) and not verify_password("wrong-password-123", stored)


def test_same_password_gives_different_hashes():
    assert hash_password(PW) != hash_password(PW)             # random salt each time


def test_duplicate_username_is_409(anon_client):
    name = _name()
    anon_client.post("/api/v1/auth/register", json={"username": name, "password": PW})
    r = anon_client.post("/api/v1/auth/register", json={"username": name.upper(), "password": PW})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "username_taken"


def test_short_password_is_rejected(anon_client):
    r = anon_client.post("/api/v1/auth/register", json={"username": _name(), "password": "short1"})
    assert r.status_code == 422


def test_cannot_self_register_as_admin(anon_client):
    r = anon_client.post("/api/v1/auth/register",
                         json={"username": _name(), "password": PW, "role": "ADMIN"})
    assert r.status_code == 422                                # mass-assignment blocked
