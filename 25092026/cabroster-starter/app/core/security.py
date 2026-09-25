"""Password hashing and JWT helpers (DEV-03).

Test Contract:
  * hash_password(plain) -> str must exist here (tests use it to create the first ADMIN).
  * Tokens are HS256, signed with settings.JWT_SECRET_KEY, claims: sub (str user id), role, exp.
  * exp must use the REAL clock: datetime.now(timezone.utc) — never get_now().
"""
from datetime import datetime, timedelta, timezone

import bcrypt  # noqa: F401  (or passlib[bcrypt])
import jwt  # noqa: F401    (PyJWT)

from app.config import settings  # noqa: F401


def hash_password(plain: str) -> str:
    # TODO: return a bcrypt hash (use settings.BCRYPT_ROUNDS)
    raise NotImplementedError("DEV-03 hash_password")


def verify_password(plain: str, hashed: str) -> bool:
    # TODO
    raise NotImplementedError("DEV-03 verify_password")


def create_access_token(user_id: int, role: str) -> str:
    # TODO: payload {"sub": str(user_id), "role": role, "exp": now_utc + 60 min}
    raise NotImplementedError("DEV-03 create_access_token")


def decode_access_token(token: str) -> dict:
    # TODO: decode + verify signature and expiry; let jwt.PyJWTError propagate
    raise NotImplementedError("DEV-03 decode_access_token")
