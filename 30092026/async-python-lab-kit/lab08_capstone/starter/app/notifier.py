"""Notification sending: timeouts + retries + parallel channels."""
import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

NOTIFY_DELAY = float(os.getenv("NOTIFY_DELAY", "1.0"))    # simulated vendor latency (s)
CALL_TIMEOUT = float(os.getenv("NOTIFY_TIMEOUT", "3.0"))  # per-call timeout (s)


class GatewayError(Exception):
    """Transient vendor failure - worth retrying."""


async def send_email(to: str, text: str) -> str:
    await asyncio.sleep(NOTIFY_DELAY)
    return f"email:{to}"


async def send_sms(phone: str, text: str) -> str:
    await asyncio.sleep(NOTIFY_DELAY)
    if not phone.startswith("+"):
        raise GatewayError(f"SMS gateway rejected {phone!r}")
    return f"sms:{phone}"


async def with_retry(make_call: Callable[[], Awaitable[T]], attempts: int = 3,
                     base_delay: float = 0.1, timeout: float = CALL_TIMEOUT) -> T:
    """TODO 2: call make_call() up to `attempts` times.
    - each attempt limited by  async with asyncio.timeout(timeout):
    - on GatewayError or TimeoutError: if last attempt -> raise, else
      await asyncio.sleep(base_delay * 2 ** (attempt - 1)) and try again
    (Hint: Lab 4 solution)"""
    raise NotImplementedError("TODO 2")


async def notify(email: str, phone: str, text: str) -> dict[str, str]:
    """Send email and SMS. Returns {"email": "SENT"|"FAILED: ...", "sms": ...}; never raises.
    TODO 3: this version is SEQUENTIAL and takes 2 x NOTIFY_DELAY.
            Use asyncio.gather(..., return_exceptions=True) to send both IN PARALLEL."""
    status: dict[str, str] = {}
    for channel, make_call in (("email", lambda: send_email(email, text)),
                               ("sms", lambda: send_sms(phone, text))):
        try:
            await with_retry(make_call)
            status[channel] = "SENT"
        except Exception as exc:
            status[channel] = f"FAILED: {exc}"
    return status
