"""API 1 - POST /api/v1/auth/token (A07 Authentication Failures)."""
import math
import time
from collections import deque

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from .errors import ApiError, validation
from .http_utils import has_control_chars, read_json_object, reject_unknown_fields
from .logging_utils import log_event
from .security import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth")
GENERIC = ApiError(401, "invalid_credentials", "Invalid username or password")


class LoginGuard:
    """Per-IP rate limit (sliding 60 s window) + per-account lockout."""

    def __init__(self, settings):
        self.s = settings
        self.hits: dict[str, deque] = {}
        self.failures: dict[str, int] = {}
        self.locked_until: dict[str, float] = {}

    def check_rate(self, ip: str):
        now = time.monotonic()
        q = self.hits.setdefault(ip, deque())
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= self.s.login_rate_limit_per_minute:
            retry = max(1, math.ceil(60 - (now - q[0])))
            log_event("rate_limited", "WARNING", client_ip=ip, path="/api/v1/auth/token")
            raise ApiError(429, "rate_limited", "Too many requests, try again later",
                           headers={"Retry-After": str(retry)})
        q.append(now)

    def is_locked(self, username: str) -> bool:
        return self.locked_until.get(username, 0) > time.monotonic()

    def fail(self, username: str):
        n = self.failures.get(username, 0) + 1
        self.failures[username] = n
        if n >= self.s.lockout_threshold:
            self.locked_until[username] = time.monotonic() + self.s.lockout_seconds
            self.failures[username] = 0
            log_event("account_locked", "WARNING", username=username)

    def success(self, username: str):
        self.failures.pop(username, None)


def _validate(body: dict) -> tuple[str, str]:
    reject_unknown_fields(body, {"username", "password"})
    u, p = body.get("username"), body.get("password")
    if not isinstance(u, str) or not 1 <= len(u) <= 64 or has_control_chars(u):
        raise validation("username must be a string of 1-64 characters", "username")
    if not isinstance(p, str) or not 1 <= len(p) <= 128:
        raise validation("password must be a string of 1-128 characters", "password")
    return u, p


@router.post("/token")
async def login(request: Request):
    st = request.app.state
    ip = request.client.host if request.client else "unknown"
    st.login_guard.check_rate(ip)
    username, password = _validate(await read_json_object(request, st.settings.max_body_bytes))

    user = st.store.by_username.get(username)
    ok = await run_in_threadpool(verify_password, password, user.password_hash if user else None)

    if user is not None and st.login_guard.is_locked(username):
        log_event("login_failed", "WARNING", username=username, reason="locked")
        raise GENERIC
    if not ok:
        if user is not None:
            st.login_guard.fail(username)
        log_event("login_failed", "WARNING", username=username[:64], reason="bad_credentials")
        raise GENERIC
    if not user.is_active:
        log_event("login_failed", "WARNING", username=username, reason="inactive")
        raise GENERIC

    st.login_guard.success(username)
    token = create_access_token(user.id, st.settings)
    log_event("login_success", user_id=user.id, username=username)
    return JSONResponse({"access_token": token, "token_type": "Bearer",
                         "expires_in": st.settings.token_ttl_seconds})
