"""In-memory bank ledger. In real life this would be a database."""
import asyncio
from dataclasses import dataclass, field


class TransferError(Exception):
    """Business rule violation (unknown account, insufficient funds, ...)."""


@dataclass
class Account:
    account_id: str
    owner_email: str
    phone: str
    balance: float


@dataclass
class Bank:
    accounts: dict[str, Account] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def _db_roundtrip(self) -> None:
        await asyncio.sleep(0.01)  # simulated DB latency - this 'await' is where races happen

    async def transfer(self, src: str, dst: str, amount: float) -> None:
        if src not in self.accounts or dst not in self.accounts:
            raise TransferError("account not found")
        if src == dst:
            raise TransferError("cannot transfer to the same account")
        # TODO 1 (race condition): run  pytest tests/test_bank.py  -> the concurrency test FAILS.
        #   Two requests both read balance 500 before either debits -> overdraft.
        #   Fix: wrap the read-check-write below in   async with self._lock:
        await self._db_roundtrip()                    # read balance
        if self.accounts[src].balance < amount:
            raise TransferError("insufficient funds")
        await self._db_roundtrip()                    # write balances
        self.accounts[src].balance -= amount
        self.accounts[dst].balance += amount


def seed_bank() -> Bank:
    return Bank(accounts={
        "ACC-101": Account("ACC-101", "asha@example.com", "+91-98100-00101", 50_000.0),
        "ACC-102": Account("ACC-102", "rohit@example.com", "+91-98100-00102", 12_000.0),
        "ACC-103": Account("ACC-103", "meera@example.com", "INVALID", 5_000.0),  # SMS always fails
    })
