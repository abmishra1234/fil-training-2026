import asyncio

import pytest

from app.bank import Account, Bank, TransferError


def small_bank() -> Bank:
    return Bank(accounts={
        "A": Account("A", "a@x.com", "+91-1", 500.0),
        "B": Account("B", "b@x.com", "+91-2", 0.0),
    })


async def test_simple_transfer():
    bank = small_bank()
    await bank.transfer("A", "B", 200)
    assert bank.accounts["A"].balance == 300
    assert bank.accounts["B"].balance == 200


async def test_insufficient_funds():
    bank = small_bank()
    with pytest.raises(TransferError, match="insufficient"):
        await bank.transfer("A", "B", 501)


async def test_no_overdraft_under_concurrency():
    """10 concurrent transfers of 100 from an account holding 500.
    Exactly 5 may succeed. Without a lock, all 10 'see' 500 and the balance goes negative."""
    bank = small_bank()
    results = await asyncio.gather(*(bank.transfer("A", "B", 100) for _ in range(10)),
                                   return_exceptions=True)
    succeeded = [r for r in results if r is None]
    assert len(succeeded) == 5
    assert bank.accounts["A"].balance == 0
    assert bank.accounts["B"].balance == 500
