"""Password hashing + JWT helpers (Extension 6 - Tasks 1-2).

Pure functions: no FastAPI, no database. Easy to unit-test and to reuse.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt                                   # PyJWT
from pwdlib import PasswordHash

from ..config import settings

# Argon2id with library-recommended parameters (salted automatically).
_password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    # TODO Task 1: return a salted Argon2id hash of `plain` (use _password_hash)
    raise NotImplementedError("Task 1: hash_password")


def verify_password(plain: str, hashed: str) -> bool:
    # TODO Task 1: return True only if `plain` matches `hashed`
    raise NotImplementedError("Task 1: verify_password")


# TODO Task 2: define DUMMY_HASH = hash_password("...") and use it in login()
#              when the username does not exist (timing-safe login).
DUMMY_HASH = None


def create_access_token(user_id: int, role: str) -> str:
    # TODO Task 2: build the claims and sign them with settings.JWT_SECRET_KEY
    #   sub  -> str(user_id)     (PyJWT >= 2.10 REQUIRES a string)
    #   role -> role
    #   iss  -> settings.JWT_ISSUER
    #   iat  -> now (UTC),  exp -> now + ACCESS_TOKEN_EXPIRE_MINUTES
    #   NOTHING sensitive (no balance, account number, name, email)
    raise NotImplementedError("Task 2: create_access_token")


def decode_access_token(token: str) -> Dict[str, Any]:
    # TODO Task 3: jwt.decode(...) with
    #   algorithms=[settings.JWT_ALGORITHM]   <- pin it, never trust the token header
    #   issuer=settings.JWT_ISSUER
    #   options={"require": ["exp", "iat", "sub", "iss"]}
    # Let jwt.PyJWTError propagate - the caller turns it into a 401.
    raise NotImplementedError("Task 3: decode_access_token")
