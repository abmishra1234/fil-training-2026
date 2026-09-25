"""Shared FastAPI dependencies.

DONE for you : IST, get_now, to_ist, oauth2_scheme, PageParams.
YOUR TASK    : get_current_user and require_roles (DEV-03).

Test Contract: always receive the current time as `now: datetime = Depends(get_now)`
in route signatures. Never call datetime.now() inside business logic.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Query, status  # noqa: F401
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User

IST = timezone(timedelta(hours=5, minutes=30))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_now() -> datetime:
    """Single source of 'current time' for business rules. Tests override this."""
    return datetime.now(IST)


def to_ist(dt: datetime) -> datetime:
    return dt.replace(tzinfo=IST) if dt.tzinfo is None else dt.astimezone(IST)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """TODO (DEV-03):
    - decode the token; on ANY error raise 401 with header WWW-Authenticate: Bearer
    - load the user by id from 'sub' — role must come from the DB, not from the token
    - user missing or inactive -> 401
    """
    raise NotImplementedError("DEV-03 get_current_user")


def require_roles(*roles: Role):
    """TODO (DEV-03): return a dependency that yields the current user or raises 403."""
    def checker(user: User = Depends(get_current_user)) -> User:
        raise NotImplementedError("DEV-03 require_roles")

    return checker


class PageParams:
    """Use as `pg: PageParams = Depends()` — gives pg.page (>=1) and pg.size (1..100)."""

    def __init__(self, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)):
        self.page = page
        self.size = size
