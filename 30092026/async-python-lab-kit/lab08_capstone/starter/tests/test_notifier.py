import time

import pytest

from app import notifier
from app.notifier import GatewayError, notify, with_retry


async def test_retry_succeeds_after_transient_failures():
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise GatewayError("try again")
        return "ok"

    assert await with_retry(flaky, attempts=3, base_delay=0.01) == "ok"
    assert calls == 3


async def test_retry_gives_up_and_reraises():
    async def always_fails():
        raise GatewayError("down")

    with pytest.raises(GatewayError):
        await with_retry(always_fails, attempts=2, base_delay=0.01)


async def test_retry_applies_timeout():
    import asyncio

    async def hangs():
        await asyncio.sleep(10)

    t0 = time.perf_counter()
    with pytest.raises(TimeoutError):
        await with_retry(hangs, attempts=2, base_delay=0.01, timeout=0.1)
    assert time.perf_counter() - t0 < 1.0


async def test_notify_sends_channels_in_parallel():
    t0 = time.perf_counter()
    result = await notify("a@x.com", "+91-1", "hi")
    elapsed = time.perf_counter() - t0
    assert result == {"email": "SENT", "sms": "SENT"}
    # sequential would take 2 x NOTIFY_DELAY; parallel takes ~1 x
    assert elapsed < 1.6 * notifier.NOTIFY_DELAY


async def test_notify_reports_partial_failure_without_raising():
    result = await notify("a@x.com", "INVALID", "hi")
    assert result["email"] == "SENT"
    assert result["sms"].startswith("FAILED")
