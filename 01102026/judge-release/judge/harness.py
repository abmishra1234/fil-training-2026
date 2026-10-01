"""Starts the candidate API as a black-box process and talks to it over HTTP.
Language-agnostic: any stack works as long as it honours the environment contract
described in EXERCISE.md (APP_ENV, APP_PORT, JWT_SECRET, ...)."""
from __future__ import annotations

import base64
import json
import os
import secrets
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import jwt

JUDGE_DIR = Path(__file__).resolve().parent
KIT_DIR = JUDGE_DIR.parent
SEED_FILE = KIT_DIR / "seed" / "seed_data.json"
SEED = json.loads(SEED_FILE.read_text(encoding="utf-8"))
USERS = {u["username"]: u for u in SEED["users"]}
ISSUER = "expense-api"
ALLOWED_ORIGIN = "https://expenses.example.com"


def load_config() -> dict:
    cfg_path = Path(os.environ.get("JUDGE_CONFIG", JUDGE_DIR / "judge_config.json"))
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    cfg["start_cmd"] = os.environ.get("JUDGE_START_CMD", cfg.get("start_cmd"))
    wd = os.environ.get("JUDGE_WORKDIR", cfg.get("workdir", "."))
    cfg["workdir"] = str((cfg_path.parent / wd).resolve()) if not os.path.isabs(wd) else wd
    cfg.setdefault("startup_timeout_seconds", 60)
    if not cfg["start_cmd"]:
        raise RuntimeError("Set start_cmd in judge_config.json (or JUDGE_START_CMD)")
    return cfg


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class AppProcess:
    def __init__(self, overrides: dict | None = None, drop: tuple = ()):
        self.cfg = load_config()
        self.port = free_port()
        self.secret = secrets.token_urlsafe(48)
        env = dict(os.environ)
        env.update({
            "APP_ENV": "test", "APP_PORT": str(self.port), "JWT_SECRET": self.secret,
            "JWT_ISSUER": ISSUER, "ACCESS_TOKEN_TTL_SECONDS": "900",
            "CORS_ALLOWED_ORIGINS": ALLOWED_ORIGIN, "LOGIN_RATE_LIMIT_PER_MINUTE": "1000",
            "SEED_FILE": str(SEED_FILE), "PYTHONUNBUFFERED": "1",
        })
        env.update(overrides or {})
        for k in drop:
            env.pop(k, None)
        self.secret = env.get("JWT_SECRET", "")
        self.env = env
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.log_path = Path(tempfile.mkstemp(prefix="judge-app-", suffix=".log")[1])
        self.proc = None

    # ---------------------------------------------------------------- lifecycle
    def start(self, expect_failure: bool = False) -> bool:
        cmd = self.cfg["start_cmd"].replace("{port}", str(self.port))
        self._log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(cmd, shell=True, cwd=self.cfg["workdir"], env=self.env,
                                     stdout=self._log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.time() + (20 if expect_failure else self.cfg["startup_timeout_seconds"])
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.2)
        return False

    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except Exception:
                    pass
        if getattr(self, "_log", None):
            self._log.close()

    def exited_with_error(self, wait: float = 20) -> bool:
        try:
            code = self.proc.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            return False
        return code != 0

    # ---------------------------------------------------------------- logs
    def log_text(self) -> str:
        return self.log_path.read_text(encoding="utf-8", errors="replace")

    def log_events(self) -> list[dict]:
        events = []
        for line in self.log_text().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if isinstance(obj, dict) and "event" in obj:
                    events.append(obj)
        return events

    def wait_for_event(self, predicate, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for e in self.log_events():
                if predicate(e):
                    return e
            time.sleep(0.1)
        return None


class Api:
    """HTTP client + token cache bound to one running app."""

    def __init__(self, app: AppProcess):
        self.app = app
        self.http = httpx.Client(base_url=app.base_url, timeout=30)
        self._tokens: dict[str, str] = {}

    def close(self):
        self.http.close()

    def login_raw(self, username, password, **kw):
        return self.http.post("/api/v1/auth/token", json={"username": username, "password": password}, **kw)

    def token(self, username: str) -> str:
        if username not in self._tokens:
            r = self.login_raw(username, USERS[username]["password"])
            assert r.status_code == 200, f"login for {username} failed: {r.status_code} {r.text[:200]}"
            self._tokens[username] = r.json()["access_token"]
        return self._tokens[username]

    def auth(self, username: str) -> dict:
        return {"Authorization": f"Bearer {self.token(username)}"}

    def list(self, username: str | None, params=None, headers=None):
        h = dict(self.auth(username)) if username else {}
        h.update(headers or {})
        return self.http.get("/api/v1/expenses", params=params, headers=h)

    def list_all(self, username: str) -> list[dict]:
        r = self.list(username, {"page_size": "100"})
        assert r.status_code == 200, r.text[:200]
        return r.json()["items"]

    def status_of(self, expense_id: int) -> str:
        return {e["id"]: e["status"] for e in self.list_all("farah")}[expense_id]

    def decide(self, username, expense_id, body=None, key=None, headers=None, raw=None):
        h = dict(self.auth(username)) if username else {}
        h["Idempotency-Key"] = key or ("judge-" + secrets.token_hex(8))
        if headers:
            h.update(headers)
        url = f"/api/v1/expenses/{expense_id}/decision"
        if raw is not None:
            return self.http.post(url, content=raw, headers=h)
        return self.http.post(url, json=body if body is not None else {"decision": "APPROVE"}, headers=h)

    # ---------------------------------------------------------------- token forging
    def mint(self, claims: dict | None = None, secret: str | None = None, alg: str = "HS256",
             drop: tuple = (), ttl: int = 600) -> str:
        now = int(time.time())
        base = {"sub": "1", "iss": ISSUER, "iat": now, "exp": now + ttl}
        base.update(claims or {})
        for k in drop:
            base.pop(k, None)
        return jwt.encode(base, secret or self.app.secret, algorithm=alg)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unsigned_token(claims: dict, alg: str = "none") -> str:
    header = b64url(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    payload = b64url(json.dumps(claims).encode())
    return f"{header}.{payload}."


def decode_segment(seg: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4)))
