"""A04 + A07: Argon2id password hashing and short-lived, pinned-algorithm JWTs."""
import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()          # Argon2id, random salt per hash
DUMMY_HASH = _hasher.hash("dummy-password-for-timing-equalisation")
ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str | None) -> bool:
    # Always run one Argon2 verify, even for unknown users, so timing does not leak existence.
    ok = _hasher.verify(plain, hashed or DUMMY_HASH)
    return ok and hashed is not None


def create_access_token(user_id: int, settings) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "iss": settings.jwt_issuer, "iat": now,
              "exp": now + timedelta(seconds=settings.token_ttl_seconds),
              "jti": uuid.uuid4().hex}          # minimal claims: no PII, no role
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str, settings) -> int:
    """Returns the user id or raises jwt.PyJWTError / ValueError."""
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM],   # pinned
                        issuer=settings.jwt_issuer,
                        options={"require": ["exp", "iat", "sub", "iss"]})
    sub = claims["sub"]
    if not isinstance(sub, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", sub):
        raise ValueError("bad sub")
    return int(sub)
