"""Capstone - Mini Bank with an async notification pipeline.

Run:  fastapi dev app/main.py     then open http://127.0.0.1:8000/docs
Test: pytest -v

Flow:  POST /transfers -> move money (locked) -> enqueue job -> 202 Accepted
       N worker tasks (started in lifespan) consume the queue -> notify() -> update status
       GET /transfers/{id} -> see notification status go QUEUED -> SENDING -> SENT/FAILED
"""
import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.bank import TransferError, seed_bank
from app.notifier import notify

log = logging.getLogger("uvicorn.error")
WORKERS = int(os.getenv("NOTIFY_WORKERS", "3"))


class TransferRequest(BaseModel):
    from_account: str = Field(examples=["ACC-101"])
    to_account: str = Field(examples=["ACC-102"])
    amount: float = Field(gt=0, le=1_000_000, examples=[1500.0])


class TransferRecord(BaseModel):
    transfer_id: str
    from_account: str
    to_account: str
    amount: float
    notification_status: str = "QUEUED"
    channels: dict[str, str] = {}


async def notification_worker(name: str, app: FastAPI) -> None:
    """TODO 4: loop forever:
        transfer_id = await queue.get()
        record = app.state.transfers[transfer_id]; set record.notification_status = "SENDING"
        look up the sender account (app.state.bank.accounts[record.from_account])
        record.channels = await notify(sender.owner_email, sender.phone, text)
        status = "SENT" if every channel is "SENT" else "PARTIAL_FAILURE"
        on unexpected exception -> "FAILED"
        ALWAYS queue.task_done() in a finally block"""
    queue: asyncio.Queue[str] = app.state.queue
    while True:
        await asyncio.sleep(3600)  # replace this placeholder with the real loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    app.state.bank = seed_bank()
    app.state.transfers = {}
    app.state.queue = asyncio.Queue(maxsize=1000)
    # TODO 5: start WORKERS background tasks running notification_worker(f"worker-{i}", app)
    workers: list[asyncio.Task] = []
    log.info("started %d notification workers", WORKERS)
    yield
    # ---- shutdown: give in-flight jobs a chance, then stop workers ----
    try:
        async with asyncio.timeout(5):
            await app.state.queue.join()
    except TimeoutError:
        log.warning("shutdown: %d notifications not sent", app.state.queue.qsize())
    for w in workers:
        w.cancel()
    await asyncio.gather(*workers, return_exceptions=True)


app = FastAPI(title="Mini Bank - Capstone", lifespan=lifespan)


@app.post("/transfers", status_code=status.HTTP_202_ACCEPTED)
async def create_transfer(req: TransferRequest, request: Request) -> dict:
    state = request.app.state
    try:
        await state.bank.transfer(req.from_account, req.to_account, req.amount)
    except TransferError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transfer_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    state.transfers[transfer_id] = TransferRecord(transfer_id=transfer_id, **req.model_dump())
    await state.queue.put(transfer_id)   # hand off; do NOT wait for notifications
    return {"transfer_id": transfer_id, "notification_status": "QUEUED",
            "status_url": f"/transfers/{transfer_id}"}


@app.get("/transfers/{transfer_id}")
async def get_transfer(transfer_id: str, request: Request) -> TransferRecord:
    record = request.app.state.transfers.get(transfer_id)
    if record is None:
        raise HTTPException(status_code=404, detail="transfer not found")
    return record


@app.get("/accounts/{account_id}")
async def get_account(account_id: str, request: Request) -> dict:
    acc = request.app.state.bank.accounts.get(account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail="account not found")
    return {"account": acc.account_id, "balance": acc.balance}


@app.get("/health")
async def health(request: Request) -> dict:
    return {"status": "ok", "queue_depth": request.app.state.queue.qsize()}
