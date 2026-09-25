"""Password hashing + JWT helpers (Extension 6 - Tasks 1-3).

Pure functions: no FastAPI, no database. Easy to unit-test and to reuse.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt                                   # PyJWT
from pwdlib import PasswordHash

from ..config import settings

# Argon2id with library-recommended parameters (salted automatically).
_password_hash = PasswordHash.recommended()

# Used when the username does not exist, so a failed login costs the same time
# either way (stops attackers discovering valid usernames by timing).
DUMMY_HASH = _password_hash.hash("dummy-password-for-timing-safety")


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),          # PyJWT >= 2.10 requires 'sub' to be a STRING
        "role": role,                 # a hint for the UI; the server re-checks the DB
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        # NO account numbers, balances, emails, names... the payload is readable by anyone.
    }
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Verify signature, algorithm, expiry and issuer. Raises jwt.PyJWTError on ANY problem."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],        # pin it: never trust the token's own 'alg'
        issuer=settings.JWT_ISSUER,
        options={"require": ["exp", "iat", "sub", "iss"]},
    )
