"""AuthN -> AuthZ pipeline as FastAPI dependencies."""
import jwt
from fastapi import Request

from .errors import forbidden, not_authenticated
from .logging_utils import log_event
from .security import decode_access_token
from .store import User


def get_current_user(request: Request) -> User:
    st = request.app.state
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        log_event("auth_failed", "WARNING", reason="missing_or_malformed_header", path=request.url.path)
        raise not_authenticated()
    try:
        user_id = decode_access_token(token.strip(), st.settings)
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        log_event("auth_failed", "WARNING", reason=type(exc).__name__, path=request.url.path)
        raise not_authenticated() from None
    user = st.store.users.get(user_id)           # stateless != blind: re-load the user
    if user is None or not user.is_active:
        log_event("auth_failed", "WARNING", reason="unknown_or_inactive_user", path=request.url.path)
        raise not_authenticated()
    request.state.user_id = user.id
    return user


def require_role(user: User, *roles: str, request: Request | None = None) -> None:
    if user.role not in roles:                   # role comes from the store, never the token
        log_event("access_denied", "WARNING", user_id=user.id, reason="role",
                  path=request.url.path if request else None)
        raise forbidden()
