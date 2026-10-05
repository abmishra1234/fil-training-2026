"""A09: structured JSON security events on stdout; secrets are never written."""
import json
import sys
import time
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
SENSITIVE = {"password", "token", "access_token", "authorization", "secret", "jwt_secret"}


def log_event(event: str, level: str = "INFO", **fields) -> None:
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "level": level,
              "event": event, "request_id": request_id_var.get()}
    for k, v in fields.items():
        record[k] = "***" if k.lower() in SENSITIVE else v
    sys.stdout.write(json.dumps(record, default=str) + "\n")
    sys.stdout.flush()
